# NELL Demo (`nell.py`) — Design

**Status:** design — a standalone example, not part of the `leto` package.
**Date:** 2026-07-03
**Grounds:** LETO II vision §8.7 (never-ending learner demo), §3 (engine-not-agent).
Builds on the shipped LETO library (VS1 + consolidation) and consumes
`lovelaice` as an agentic framework **as a library**.

> The demo re-does NELL (never-ending, web-driven knowledge accumulation) with a
> deliberately **dumb agent** and a **super-simple prompt**, so that the coherent
> growth of the knowledge base is unambiguously attributable to **LETO** — not to
> the agent's cleverness or its own memory. The agent's only memory *is* LETO.

## 1. Purpose & thesis

A single-file CLI, `repos/leto/examples/nell.py`, that — given a topic — runs a
`lovelaice` ReAct agent in a never-ending loop to build a small topic "wiki" (a
folder of LETO markdown notes). The point is demonstrative:

- **LETO does the work.** The agent is stateless across cycles; its entire
  cross-cycle memory is the LETO vault. Recall drives what it does next. Remove
  LETO and the agent is a goldfish. This is an ablation, not a limitation.
- **The prompt is trivial.** No elaborate scaffolding. The organizing intelligence
  (entity resolution, provenance, settlement maturation) lives in `leto.settle()`,
  not the prompt.
- **The artifact is the vault.** The growing markdown notes *are* the wiki, and
  they are inspectable outside the demo.

## 2. Scope

**In:**
- One topic per run. Pure-agent loop (lovelaice ReAct owns each cycle's decisions).
- LETO consumed as a **library** (not via its MCP surface, which doesn't exist yet).
- lovelaice consumed as a **library** (no `.lovelaice.py`, no lovelaice CLI).
- Web search via DuckDuckGo (`ddgs`, keyless); page fetch via lovelaice's built-in
  `web.fetch` tool, reused as-is.
- Per-cycle console report of vault growth (notes, merges, settlement promotions).

**Out (YAGNI):**
- Associative/Hebbian layer, MCP surface, multi-topic runs.
- Comparative NELL benchmarking / metrics beyond the growth report.
- Any `.lovelaice.py` config file. Everything is wired in code in `nell.py`.
- Persisting the agent's conversation across cycles (by design — see §1).

## 3. Architecture — one file, three wirings

`nell.py` builds three things over **one shared `lingo.LLM`**:

1. **The knowledge engine (LETO).** A `leto.Engine` over a vault folder, wired with
   the lingo-backed backends and a local extractor (§4).
2. **The agent (lovelaice).** A `lovelaice.core.Lovelaice(llm, prompt)` with tools
   registered in code (§5).
3. **The loop (CLI driver).** An outer `while` that runs one fresh agent turn per
   cycle and reports vault growth (§6).

### Confirmed library APIs (grounded against the installed code)

- **lovelaice** (`lovelaice.core.Lovelaice`): `Lovelaice(llm: LLM, prompt: str)`;
  register a tool with `agent.tool(func)` (the function's docstring becomes the
  LLM-facing description, annotated params become the schema); run one full ReAct
  turn with `await agent.chat(prompt) -> Message` (a single turn does many
  tool-calls internally until the agent produces a final message). Reuse the
  built-in fetch via `from lovelaice.tools.web import fetch`.
- **lingo**: `LLM(model=, api_key=, base_url=, ...)`; `Engine(llm)` and
  `await engine.create(Context(), Model, prompt) -> Model` for the LETO backends
  and the extractor.
- **leto**: `NoteStore(folder, db_path)`, `Engine(store, extractor, embedder,
  judge, merger, gate)`, `engine.ingest(text, source) -> list[Note]`,
  `engine.settle() -> SettleReport`, `engine.recall(query) -> KnowledgeBlob`.
  Backends: `leto.backends_lingo.lingo_embedder/lingo_judge/lingo_merger/lingo_gate`.

## 4. The LETO extractor (lives in `nell.py`)

`leto.Engine.ingest` requires an injected `Extractor = Callable[[str],
list[ExtractedItem]]`, and `leto.backends_lingo` does **not** provide one (it only
covers embedder/judge/merger/gate). So `nell.py` defines a lingo-backed extractor:

- A local sync `extractor(text) -> list[ExtractedItem]` that runs one structured
  `lingo.Engine.create` pass (bridged async→sync with `asyncio.run`, matching the
  `backends_lingo` pattern) over the fetched page text, returning entities +
  procedures with titles, bodies, and link titles.
- Prompted to extract atomic notes about the topic domain, not to summarize the
  page. Non-deterministic; not unit-tested (see §8).

## 5. Tools the agent sees

Registered in code via `agent.tool(...)`. Each wraps the module-level `leto.Engine`
/ search and returns a short string (tool results are stringified into context).

- `leto_recall(query: str) -> str` — what the vault already knows: top notes with
  their settlement level and sources. This is how the agent "remembers" and finds
  gaps.
- `leto_ingest(text: str, source: str) -> str` — extract + index notes from fetched
  page text; `source` is the URL. Returns the slugs created.
- `leto_settle() -> str` — run consolidation once; returns a summary of the
  `SettleReport` (clusters merged, notes promoted).
- `web_search(query: str) -> str` — DuckDuckGo via `ddgs`; returns a short list of
  `title / url / snippet`.
- `fetch` — lovelaice's built-in `web.fetch`, reused unchanged, to pull page text.

## 6. The loop

CLI: `nell.py <topic> [--cycles N] [--vault DIR] [--model SLUG]`.

- `--cycles` default **8**; `Ctrl-C` stops early and prints the final state.
- `--vault` default a timestamped scratch dir; the notes folder + beaver db live here.
- `--model` an OpenRouter model slug; falls back to an env default. API creds via
  env (`OPENROUTER_API_KEY`, OpenRouter base URL) read by `lingo.LLM`.

Per cycle:

1. Build a **fresh** `Lovelaice` agent (state lives only in the vault).
2. `await agent.chat(CYCLE_PROMPT.format(topic=topic))`. One ReAct turn in which
   the agent, on its own: recalls what it knows → identifies a gap → does **several**
   `web_search` + `fetch` + `leto_ingest` rounds until satisfied → calls
   `leto_settle` **once** → reports what it learned as the final message.
3. `nell.py` inspects the vault (`store.all_notes()`) and prints a growth line:
   note count, notes by settlement level, and the merges/promotions from this
   cycle's settle.
4. Restart with a fresh agent.

Errors in a cycle (web/LLM failures, tool exceptions) are logged and the loop
continues to the next cycle.

### The cycle prompt (super-simple — the whole point)

Roughly:

> You are a never-ending learner studying **{topic}**. Your memory is LETO — you
> remember nothing on your own. First call `leto_recall` to see what you already
> know and pick a gap. Then use `web_search` and `fetch` as many times as you need
> to research that gap, calling `leto_ingest(text, source)` on what you find. When
> satisfied, call `leto_settle` once, then briefly report what you learned this
> cycle.

## 7. Artifact & reporting

- **The vault** — a folder of markdown notes (entities + procedures) with
  frontmatter (settlement, sources, links, aliases). Inspectable in Obsidian or any
  editor; this is the "wiki" the demo builds.
- **Per-cycle console report** — one line: `cycle i · N notes (fleeting F /
  developing D / established E) · merged M · promoted P`.
- **Final recall dump** — after the loop, one `engine.recall(topic)` printed as the
  closing snapshot.

## 8. Testing

Like `leto.backends_lingo`, `nell.py` hits a **real LLM and the real web**, so it is
**not** part of the automated suite — it is **verified by manual smoke**: run it on a
concrete topic for a couple of cycles and confirm (a) notes appear in the vault, (b)
`settle` merges duplicates across cycles, (c) settlement advances as sources
accumulate, (d) the per-cycle report reflects the growth. Any genuinely pure helper
(e.g., the growth-report formatter) may carry a tiny deterministic unit test, but
no test calls an LLM, the web, or an embedder.

## 9. How to run (documented in the module docstring)

The example runs in an environment that has `leto`, `lovelaice`, `lingo`, and
`ddgs` installed, with OpenRouter credentials in the environment. It is intentionally
decoupled from `leto`'s own dependencies — installing it is a manual step, not a
`leto` extra.

## 10. Out of scope (restated)

Associative layer, MCP surface, multi-topic, comparative metrics, `.lovelaice.py`
config, cross-cycle conversational memory.
