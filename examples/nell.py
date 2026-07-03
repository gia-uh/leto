#!/usr/bin/env python
"""nell.py — a never-ending learner demo on LETO + lovelaice.

Given a TOPIC, runs a lovelaice ReAct agent in a loop to build a small
"wiki" of LETO markdown notes. The agent is stateless across cycles — its
only memory is the LETO vault. This demonstrates that LETO does the work,
not the agent's cleverness or its own memory.

LETO is async-native, so the whole run lives on ONE event loop: the store,
the agent, and the LLM-backed deps all share it — no bridges, no per-call
client churn.

Run (in an env with `leto`, `lovelaice`, `lingo-ai`, `ddgs` installed):

    export OPENROUTER_API_KEY=sk-...
    python nell.py "History of the Enigma machine" --model anthropic/claude-haiku-4.5 --cycles 4

The chat model is any OpenRouter slug (--model or NELL_MODEL). Embeddings are
computed locally (no embeddings provider needed). Web search uses DuckDuckGo.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from lingo import LLM, Context, Engine as LingoEngine, tool as as_tool
from pydantic import BaseModel

from leto import Engine, ExtractedItem, MergedGroup, Note, NoteStore, SettleReport, Settlement
from ddgs import DDGS
from lovelaice.tools.web import fetch                      # reused lovelaice tool
from lovelaice.agent.agent import Agent, AgentConfig
from lovelaice.agent.loops import ReActNative
from lovelaice.agent.tools import AgentTool

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EMB_DIM = 256


def make_llm(model: str) -> LLM:
    return LLM(
        model=model,
        api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY"),
        base_url=OPENROUTER_BASE_URL,
    )


# --- LETO's injected deps (async) -----------------------------------------

async def _hash_embedder(text: str) -> list[float]:
    """Deterministic, keyless bag-of-tokens embedding. A stand-in for a real
    embedding model — swap in `lingo.Embedder` if you have an embeddings API."""
    vec = [0.0] * EMB_DIM
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % EMB_DIM] += 1.0
    return vec


class _Extraction(BaseModel):
    """Atomic factual/procedural notes extracted from a page."""
    items: list[ExtractedItem]


class _Resolution(BaseModel):
    """The resolver's verdict on a candidate cluster: zero or more confirmed
    same-entity groups."""
    groups: list[MergedGroup]


class _Approve(BaseModel):
    """Whether a note is coherent/complete enough to advance a settlement level."""
    approve: bool


_Extraction.model_rebuild()   # resolve list[ExtractedItem] forward ref
_Resolution.model_rebuild()   # resolve list[MergedGroup] forward ref


def make_deps(model: str):
    """Build LETO's async deps (extractor, judge, merger, gate, embedder),
    all sharing one lingo Engine on the caller's event loop."""
    lengine = LingoEngine(make_llm(model))

    async def extractor(text: str) -> list[ExtractedItem]:
        prompt = (
            "Extract atomic knowledge notes from the text below. Each note is "
            "an entity (a thing/person/concept) or a procedure (a how-to), with "
            "a short title, a 1-3 sentence body, and links (titles of related "
            "notes). Extract the durable knowledge, do not summarize the page.\n\n"
            + text
        )
        return (await lengine.create(Context([]), _Extraction, prompt)).items

    async def merger(notes: list[Note]) -> list[MergedGroup]:
        # ONE LLM call per candidate cluster: decide which members are the SAME
        # entity (strict — not merely related) and fuse each group.
        listing = "\n".join(f"- [{n.slug}] {n.title}: {n.body}" for n in notes)
        prompt = (
            "Below is a candidate cluster of knowledge notes (each with a "
            "[slug]). They were grouped only by surface similarity, so some may "
            "be the SAME real-world entity and others merely related.\n\n"
            "Group ONLY the notes that are the same specific entity (same person, "
            "place, organization, device, method, or concept — possibly under "
            "different names/spellings). Do NOT group merely related things: a "
            "person vs. a thing they made; a place vs. someone who worked there; "
            "a method vs. its inventor; a whole vs. its parts. Example: 'Alan "
            "Turing'/'Turing, Alan' are the SAME; 'Arthur Scherbius'/'Enigma "
            "machine' are NOT.\n\n"
            "For each same-entity group of 2+ notes, return its member slugs and "
            "a fused canonical title + body (no duplication). Omit singletons.\n\n"
            f"{listing}"
        )
        return (await lengine.create(Context([]), _Resolution, prompt)).groups

    async def gate(note: Note, level: Settlement) -> bool:
        prompt = (
            f"Note {note.title}: {note.body}\nIt has {len(set(note.sources))} "
            f"corroborating sources. Coherent/complete enough to be '{level.value}'?"
        )
        return (await lengine.create(Context([]), _Approve, prompt)).approve

    return extractor, merger, gate, _hash_embedder


async def build_engine(vault: Path, model: str) -> tuple[Engine, NoteStore]:
    store = await NoteStore.open(folder=vault / "notes", db_path=vault / "leto.db")
    extractor, merger, gate, embedder = make_deps(model)
    engine = Engine(store, extractor, embedder, merger=merger, gate=gate)
    return engine, store


# --- tools the agent sees --------------------------------------------------

def _format_blob(blob) -> str:
    lines = [
        f"- [{r.note.settlement.value}] {r.note.title} (sources: {len(set(r.note.sources))})"
        for r in blob.facts + blob.procedures
    ]
    return "\n".join(lines) or "(nothing known yet)"


def make_leto_tools(engine: Engine, state: dict):
    async def leto_recall(query: str) -> str:
        """Recall what the knowledge base already knows about `query`: known
        notes with their settlement level and source count. Call this FIRST
        each cycle to see what you know and pick a gap."""
        return _format_blob(await engine.recall(query))

    async def leto_ingest(text: str, source: str) -> str:
        """Extract and store atomic notes from page `text`. `source` is the
        page URL (its provenance). Call on each useful page you fetch."""
        notes = await engine.ingest(text, source)
        return f"ingested {len(notes)} notes: " + ", ".join(n.slug for n in notes)

    async def leto_settle() -> str:
        """Consolidate: merge duplicate entities and mature well-sourced notes.
        Call ONCE at the end of a cycle, after ingesting."""
        report = await engine.settle()
        state["last_report"] = report
        return f"merged {len(report.merged)} clusters, promoted {len(report.promoted)} notes"

    return leto_recall, leto_ingest, leto_settle


async def web_search(query: str) -> str:
    """Search the web (DuckDuckGo). Returns up to 5 results, one per line as
    `title — url — snippet`. Use to find pages about a gap, then `fetch` a URL."""
    def _search():
        return DDGS().text(query, max_results=5)
    results = await asyncio.to_thread(_search)   # ddgs is blocking; offload it
    return "\n".join(f"{r['title']} — {r['href']} — {r['body']}"
                     for r in results) or "no results"


SYSTEM_PROMPT = (
    "You are a never-ending learner. Your memory is LETO — you remember nothing "
    "on your own; everything you know lives in the knowledge base, reachable via "
    "leto_recall. Keep your knowledge growing and consolidated."
)

CYCLE_PROMPT = (
    "Study the topic: {topic}.\n"
    "1. Call leto_recall('{topic}') to see what you already know, and pick ONE gap.\n"
    "2. Use web_search and fetch as many times as you need to research that gap; "
    "call leto_ingest(text, source) on each useful page (source = its URL).\n"
    "3. When satisfied, call leto_settle once.\n"
    "4. Briefly report what you learned this cycle."
)


def build_agent(engine: Engine, model: str, state: dict, session_path: Path) -> Agent:
    """A fresh lovelaice native-ReAct agent. State lives only in the LETO vault,
    so each cycle gets a fresh session."""
    leto_recall, leto_ingest, leto_settle = make_leto_tools(engine, state)
    tools = [
        AgentTool(inner=as_tool(leto_recall), kind="read"),
        AgentTool(inner=as_tool(leto_ingest), kind="edit"),
        AgentTool(inner=as_tool(leto_settle), kind="other"),
        AgentTool(inner=as_tool(web_search), kind="search"),
        AgentTool(inner=as_tool(fetch), kind="fetch"),
    ]
    config = AgentConfig(
        model=model, system_prompt=SYSTEM_PROMPT,
        api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY"),
        base_url=OPENROUTER_BASE_URL, max_tokens=4096,
    )
    agent = Agent(config=config, tools=tools, loop=ReActNative(),
                  session_path=session_path)
    agent.on("tool_execution_start", lambda ev: print(f"  · {ev.name}", flush=True))
    return agent


def _final_answer(agent: Agent) -> str:
    for m in reversed(agent.messages_for_llm()):
        if m.role == "assistant" and str(getattr(m, "content", "") or "").strip():
            return str(m.content)
    return ""


def format_cycle_report(cycle: int, notes: list[Note], report: SettleReport) -> str:
    by = Counter(n.settlement.value for n in notes)
    return (f"cycle {cycle} · {len(notes)} notes "
            f"(fleeting {by['fleeting']} / developing {by['developing']} / "
            f"established {by['established']}) · merged {len(report.merged)} "
            f"· promoted {len(report.promoted)}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Never-ending learner demo on LETO + lovelaice.")
    p.add_argument("topic", help="the topic to learn about")
    p.add_argument("--cycles", type=int, default=8, help="number of learning cycles (default 8)")
    p.add_argument("--vault", default=None, help="vault dir (default: ./.nell-<timestamp>)")
    p.add_argument("--model", default=None, help="OpenRouter chat model slug (or set NELL_MODEL)")
    return p.parse_args()


async def run(topic: str, model: str, cycles: int, vault: Path) -> None:
    (vault / "sessions").mkdir(parents=True, exist_ok=True)
    engine, store = await build_engine(vault, model)
    print(f"topic: {topic!r} · model: {model} · vault: {vault}")
    try:
        for cycle in range(1, cycles + 1):
            print(f"\n=== cycle {cycle}/{cycles} ===", flush=True)
            state: dict = {}
            agent = build_agent(engine, model, state, vault / "sessions" / f"c{cycle}.json")
            try:
                await agent.prompt(CYCLE_PROMPT.format(topic=topic))
                print("\n" + _final_answer(agent))
            except Exception as e:               # a cycle may fail; keep going
                print(f"  cycle error: {type(e).__name__}: {e}", flush=True)
            notes = await store.all_notes()
            print(format_cycle_report(cycle, notes, state.get("last_report") or SettleReport()))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\ninterrupted — stopping.")
    finally:
        print("\n=== final recall ===")
        print(_format_blob(await engine.recall(topic)))
        await store.close()


def main() -> None:
    args = parse_args()
    model = args.model or os.getenv("NELL_MODEL")
    if not model:
        sys.exit("error: set --model <openrouter-slug> or NELL_MODEL")
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY")):
        sys.exit("error: set OPENROUTER_API_KEY")
    vault = Path(args.vault or f".nell-{datetime.now():%Y%m%d-%H%M%S}")
    asyncio.run(run(args.topic, model, args.cycles, vault))


if __name__ == "__main__":
    main()
