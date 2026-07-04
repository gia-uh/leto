# LETO — Vision (revised): the zero-LLM knowledge substrate for agents

**Status:** vision. **Date:** 2026-07-04.
**Supersedes:** `2026-07-03-leto-ii-vision.md` (the "engine with injected LLM
passes" framing). Kept for the record; this document is the north star.

## The pivot

The previous vision made LETO an engine that *takes* the LLM as injected
callables (`extractor`, `judge`, `merger`, `gate`). Shipped code (VS1 +
consolidation, now async) works that way. This revision removes the LLM from
LETO entirely.

The reason is concrete and economic. LETO's first real consumer is **an agent's
memory** — e.g. Claude Code maintaining the whole workspace's knowledge instead
of a pile of loose markdown. But that agent is *already* a frontier LLM in the
loop, already paid for. Having LETO call a **second** LLM by API to judge/merge
is paying twice — and the second model is worse than the agent that's right
there. The intelligence belongs to the consumer. So:

> **LETO holds zero LLM. All linguistic inference lives in the external agent.**
> LETO is the substrate; the agent is the mind.

This is not a departure from the old principle ("engine, not agent") — it is its
completion. The old vision already said the agent owns the loop; this removes the
last LLM that was still hiding inside.

## What LETO is

LETO is **the best possible engine for giving any arbitrary agent an incremental
knowledge base** of three kinds of knowledge — **facts**, **procedures**, and
**experience** — stored incrementally by the agent, where LETO always provides
the best possible *view* of that knowledge: the best recall in the market for a
specific task (*"how do I do X"*) and for a specific fact (*"what is Y"*).

LETO is designed to be driven **agentically**. Its tools are so useful, so
typed, and give feedback so rich and so explicit — what failed and why, what to
do next, what else is worth reading — that **an agent becomes more capable by
the mere fact of having LETO**. LETO does no linguistic reasoning; it makes the
agent's reasoning land in a substrate that remembers, connects, and matures.

## Core principles (invariants)

- **Zero LLM inside.** No generation, no judgment, no summarization in LETO.
  Extraction, merge decisions, gating, synthesis — all the agent's.
- **The one mechanical exception: a local embedder.** Semantic recall needs
  vectors, and vectors come from a model. To keep "zero double-pay" true, LETO
  owns a **local** embedding model (on-machine, no API) — a mechanical
  vectorizer, not a reasoning model. (Pluggable, but never a metered API by
  default.)
- **Agnostic about inference, opinionated about schema and workflow.** Any agent
  can drive LETO, but LETO enforces a tight note schema (so the KB stays
  coherent across many drivers) and ships an opinionated usage/workflow guide.
- **Always agent-driven, including backfill.** No autonomous loop, no
  non-interactive batch mode. Even the first-time ingestion of an existing
  workspace is the agent reading and remembering, one note at a time. Simplicity
  over a batch fast-path.
- **CLI ≡ MCP, 1-1, over one core library.** `leto remember "note"` and
  `leto:remember(note)` are two thin adapters over the same function. The tool
  surface *is* the product; it is designed for an agent's ergonomics.
- **Beaver is the storage substrate; markdown files are canonical.** LETO adds
  the opinionated knowledge model, retrieval, and navigation on top.

## The three layers (+ the associative layer)

1. **Facts** — *what is Y*. Entity-centric notes; the commodity layer (generic
   vector stores already play here). Navigable graph of entities and relations.
2. **Procedures** — *how to X*. The know-how layer: reusable how-to knowledge,
   linked to the facts and tools it involves.
3. **Experience** — *what worked and what did not*. The novel layer and the
   spine. Schema shape: *situation/problem + context → action taken → outcome
   (worked / didn't) → lesson*. Its retrieval key is **similarity of
   situation**. This is case-based memory: it is what lets an agent stop
   repeating mistakes across sessions. The **meta-learning** we will build later
   — learning from past problem solutions — lives here.

Cross-cutting all three:

4. **The associative / usage-learning layer (100% in scope).** Recall is
   reinforced by **what the agent actually used and acted on** — a Hebbian signal
   over notes and paths. This is not optional decoration: it is *the* mechanism
   by which recall reaches "best in the market" **without** an LLM inside.
   Cosine similarity + settlement is a good recall; usage-learning is what turns
   it into a recall that gets better with every session and approximates
   task-relevance that LETO could never infer linguistically. The headline
   ("best possible recall for a task") is only true because this layer exists.

## The tool surface is the product

The design primitives that make an agent smarter by having LETO:

- **Every operation returns `{result, observations, suggested_next_actions}`.**
  The suggested actions are **ready-to-invoke** tool calls (name + args). "I
  stored two notes that look alike → to merge: `leto merge <a> <b>`." The agent
  never has to discover what to do next; LETO hands it the affordance.
- **Recall is a briefing, not a search.** Two typed modes: `how_to("X")`
  (procedures + experience, ranked by *what worked*) and `explain("Y")` (the
  fact + its immediate graph). Results are semantically annotated: settlement
  (trust), provenance (source count), navigational edges (*"also worth reading →"*),
  and consolidation nudges inline.
- **Proactive intelligence = mechanical detectors (linters over the KB).**
  "These two look mergeable." "This note references X, which doesn't exist."
  "This fact has one source and is old — confirm or demote." LETO *detects*
  mechanically and *suggests*; the agent *judges* and confirms. Zero LLM,
  deterministic, cheap.
- **Self-bootstrapping.** `leto init` (and the equivalent MCP tool) emits LETO's
  own usage/system-prompt (*"here is how you use me"*) **plus** a snapshot of
  what it already knows. A blank agent runs it and is oriented with zero external
  configuration. The workflow "policy" lives in LETO's own output, not in a
  separate skill.
- **Super typed, with explicit failure feedback.** Every error says what failed
  and how to fix the call. Outputs are structured and rich enough that an agent
  can orient itself from them alone.

## Consolidation & settlement (mechanical, agent-gated)

- **Consolidation is coupled to recall, not a batch pass.** When recall surfaces
  two notes that look like duplicates, it says so inline; the agent decides and
  confirms with one cheap `merge` call over notes it already has in context. No
  scheduled `settle()` over the whole KB — that is where agent-in-the-loop breaks
  down, and it invites the agent to skip maintenance (letting the KB rot). Making
  consolidation a byproduct of use is what keeps it actually happening.
- **Merge is one atomic operation.** The agent supplies the decision (which notes,
  canonical title/body); LETO commits the whole thing transactionally (redirect
  edges, union links + provenance, leave aliases, delete absorbed). LETO never
  exposes the raw graph primitives for the agent to sequence — that would risk
  corruption.
- **Settlement is a mechanical trust signal.** Distinct-source count drives
  eligibility (`fleeting → developing → established`); the agent gates the
  advance (is this coherent/complete enough?); `permanent` is human-only. LETO
  tracks the maturation; the agent judges the quality. The gradient tells the
  agent how much to trust a note — "seen once" vs "corroborated" — without asking
  anyone.

## What LETO provides over "just beaver"

Beaver already gives vectors, graph, FTS, and dicts. LETO's distinctive value,
zero-LLM, is: the **markdown-canonical, opinionated knowledge schema** (fact /
procedure / experience); **hybrid blocking** (vector ∪ FTS candidate generation);
**atomic merge/alias mechanics** (so refactoring memory never dangles a link);
the **settlement** trust model; the **usage-learning** recall; and above all the
**agent-ergonomic tool surface with affordances and self-bootstrap**. LETO is
the memory OS for LLM agents; beaver is the disk under it.

## Relationship to prior work

- **The superseded LETO II vision.** Same substrate goals; the change is removing
  the injected LLM callables from the core and moving *all* inference to the
  consuming agent. The current code (extractor/judge/merger/gate as injected
  callables) is what this pivot re-plans away from.
- **NELL.** The never-ending learner is now *always* an external agent driving
  LETO (the demo agent, or a real one like Claude Code). LETO provides the
  substrate; the agent provides the learning. Consistent with "the agent owns the
  loop."
- **Préstamo's bitemporal GraphRAG** (`2026-07-03-fact-kb-temporal-evolution.md`).
  Temporal evolution of facts (valid-time, as-of, correction vs evolution) is a
  future concern; in this model it becomes the agent's consolidation *policy* over
  a LETO that provides the temporal fields and mechanics — not LLM logic inside
  LETO.
- **The vault / know-how / CLAUDE.md / MEMORY.md.** These are the intuition LETO
  formalizes and the first thing it replaces: an agent's facts, procedures, and
  experience, semantically recalled and maturity-tracked instead of grepped over
  loose markdown. The dogfood is Claude Code's own memory.

## Roadmap

Deliberately open — **to be planned next.** Two things are already clear:

- The note **schema** (fields per layer, how they link in the graph) is the
  decision everything else inherits; it comes first.
- The current implementation (VS1 + consolidation, with injected LLM callables)
  must be re-planned to this vision: strip the callables, expose the mechanics as
  the CLI/MCP tool surface with affordances, add the local embedder, the
  usage-learning layer, and the self-bootstrap.

Everything above is zero-LLM inside LETO and agent-driven — consistent, and the
completion of the original "engine, not agent" principle.
