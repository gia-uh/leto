#!/usr/bin/env python
"""nell.py — a never-ending learner demo on LETO + lovelaice.

Given a TOPIC, runs a lovelaice ReAct agent in a loop to build a small
"wiki" of LETO markdown notes. The agent is stateless across cycles — its
only memory is the LETO vault. This demonstrates that LETO does the work,
not the agent's cleverness or its own memory.

Run (in an env with `leto`, `lovelaice`, `lingo-ai`, `ddgs` installed):

    export OPENROUTER_API_KEY=sk-...
    python nell.py "History of the Enigma machine" --model openai/gpt-4o --cycles 4

The chat model is any OpenRouter slug (--model or NELL_MODEL). Embeddings
are computed locally (no embeddings provider needed). Web search uses
DuckDuckGo (keyless).
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

from lingo import LLM

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def make_llm(model: str, on_token=None) -> LLM:
    """A lingo.LLM pointed at OpenRouter. A fresh instance is built per use
    so no client is reused across event loops."""
    return LLM(
        model=model,
        api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY"),
        base_url=OPENROUTER_BASE_URL,
        on_token=on_token,
    )


from lingo import Context, Engine as LingoEngine  # noqa: E402
from leto import ExtractedItem, MergedNote, Note, Settlement  # noqa: E402
from pydantic import BaseModel  # noqa: E402

EMB_DIM = 256


def _hash_embedder(text: str) -> list[float]:
    """Deterministic, keyless bag-of-tokens embedding. A stand-in for a real
    embedding model — swap in `lingo.Embedder` if you have an embeddings API."""
    vec = [0.0] * EMB_DIM
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % EMB_DIM
        vec[idx] += 1.0
    return vec


class _Extraction(BaseModel):
    """Atomic factual/procedural notes extracted from a page."""
    items: list[ExtractedItem]


class _SameEntity(BaseModel):
    """Whether two notes describe the same real-world entity."""
    same: bool


class _Approve(BaseModel):
    """Whether a note is coherent/complete enough to advance a settlement level."""
    approve: bool


def _create(model: str, out_model: type[BaseModel], prompt: str) -> BaseModel:
    """One structured LLM pass with a FRESH client. Worker-thread only
    (called via asyncio.to_thread from tools) — never on the agent's loop."""
    async def _go():
        return await LingoEngine(make_llm(model)).create(Context(), out_model, prompt)
    return asyncio.run(_go())


def make_deps(model: str):
    """Build LETO's injected dependencies (extractor, judge, merger, gate,
    embedder) bound to `model`."""

    def extractor(text: str) -> list[ExtractedItem]:
        prompt = (
            "Extract atomic knowledge notes from the text below. Each note is "
            "an entity (a thing/person/concept) or a procedure (a how-to), with "
            "a short title, a 1-3 sentence body, and links (titles of related "
            "notes). Extract the durable knowledge, do not summarize the page.\n\n"
            + text
        )
        return _create(model, _Extraction, prompt).items

    def judge(a: Note, b: Note) -> bool:
        prompt = (
            f"Note A — {a.title}: {a.body}\n\nNote B — {b.title}: {b.body}\n\n"
            "Do A and B describe the SAME real-world entity?"
        )
        return _create(model, _SameEntity, prompt).same

    def merger(notes: list[Note]) -> MergedNote:
        joined = "\n\n---\n\n".join(f"{n.title}: {n.body}" for n in notes)
        prompt = (
            "Fuse these notes about the same entity into ONE canonical note. "
            "Return a single clear title and a merged body without duplication:"
            f"\n\n{joined}"
        )
        return _create(model, MergedNote, prompt)

    def gate(note: Note, level: Settlement) -> bool:
        prompt = (
            f"Note {note.title}: {note.body}\nIt has {len(set(note.sources))} "
            f"corroborating sources. Coherent/complete enough to be '{level.value}'?"
        )
        return _create(model, _Approve, prompt).approve

    return extractor, judge, merger, gate, _hash_embedder


from leto import Engine, NoteStore  # noqa: E402


def build_engine(vault: Path, model: str) -> tuple[Engine, NoteStore]:
    store = NoteStore(folder=vault / "notes", db_path=vault / "leto.db")
    extractor, judge, merger, gate, embedder = make_deps(model)
    engine = Engine(store, extractor, embedder, judge=judge, merger=merger, gate=gate)
    return engine, store


def _format_blob(blob) -> str:
    lines = []
    for r in blob.facts + blob.procedures:
        lines.append(f"- [{r.note.settlement.value}] {r.note.title} "
                     f"(sources: {len(set(r.note.sources))})")
    return "\n".join(lines) or "(nothing known yet)"


def make_leto_tools(engine: Engine, state: dict):
    async def leto_recall(query: str) -> str:
        """Recall what the knowledge base already knows about `query`: known
        notes with their settlement level and source count. Call this FIRST
        each cycle to see what you know and pick a gap."""
        blob = await asyncio.to_thread(engine.recall, query)
        return _format_blob(blob)

    async def leto_ingest(text: str, source: str) -> str:
        """Extract and store atomic notes from page `text`. `source` is the
        page URL (its provenance). Call on each useful page you fetch."""
        notes = await asyncio.to_thread(engine.ingest, text, source)
        return f"ingested {len(notes)} notes: " + ", ".join(n.slug for n in notes)

    async def leto_settle() -> str:
        """Consolidate: merge duplicate entities and mature well-sourced notes.
        Call ONCE at the end of a cycle, after ingesting."""
        report = await asyncio.to_thread(engine.settle)
        state["last_report"] = report
        return f"merged {len(report.merged)} clusters, promoted {len(report.promoted)} notes"

    return leto_recall, leto_ingest, leto_settle


from ddgs import DDGS  # noqa: E402
from lovelaice.core import Lovelaice  # noqa: E402
from lovelaice.tools.web import fetch  # noqa: E402
from leto import SettleReport  # noqa: E402


async def web_search(query: str) -> str:
    """Search the web (DuckDuckGo). Returns up to 5 results, one per line as
    `title — url — snippet`. Use to find pages about a gap, then `fetch` a URL."""
    def _search():
        return DDGS().text(query, max_results=5)
    results = await asyncio.to_thread(_search)
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


def build_agent(engine: Engine, model: str, state: dict) -> Lovelaice:
    agent = Lovelaice(llm=make_llm(model), prompt=SYSTEM_PROMPT)
    leto_recall, leto_ingest, leto_settle = make_leto_tools(engine, state)
    for fn in (leto_recall, leto_ingest, leto_settle, web_search, fetch):
        agent.tool(fn)
    return agent


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


def main() -> None:
    args = parse_args()
    model = args.model or os.getenv("NELL_MODEL")
    if not model:
        sys.exit("error: set --model <openrouter-slug> or NELL_MODEL")
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY")):
        sys.exit("error: set OPENROUTER_API_KEY")
    vault = Path(args.vault or f".nell-{datetime.now():%Y%m%d-%H%M%S}")
    print(f"topic: {args.topic!r} · model: {model} · cycles: {args.cycles} · vault: {vault}")


if __name__ == "__main__":
    main()
