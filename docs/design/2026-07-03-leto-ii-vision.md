# LETO II — Vision & Architecture (grounding)

**Status:** grounding design — the north star for the LETO rewrite.
**Date:** 2026-07-03
**Supersedes:** the 2019 RANLP prototype (`Demo Application for LETO`) and the
Neo4j-based `leto-mvp` currently on `main`. This document grounds a full
rewrite in the same repo.

> This is a *vision* document. It fixes the concepts, the layers, the boundary,
> and the decomposition. Each sub-project below gets its own detailed
> spec → plan → implementation cycle. It does not prescribe function signatures
> or file formats beyond what is needed to pin the architecture.

---

## 1. What LETO is (and is not)

LETO is a **knowledge-discovery engine** meant to be the **backbone of any AI
application**. Feed it material, and it maintains a long-term knowledge base
that *keeps improving*; ask it about a task, and it hands back the relevant
concepts plus how things are done.

**LETO is:**

- An **engine / backend**. It may depend on embeddings, LLMs, and a database,
  but it is infrastructure, not an application.
- Consumable in **two modes**: as a **library / framework** (call engine
  methods and classes) and as an **MCP server** (so an agent can use it).
- **Domain-independent** and **consumer-independent**. It makes no assumptions
  about who is using it or what for.
- **Local and private** by default: the backend is plain-text files in a
  folder, indexed in [beaver](https://pypi.org/project/beaver-db/). No cloud
  dependency.

**LETO is not:**

- **Not an agent.** There is no autonomous loop inside LETO, no ticks, no
  self-driven behaviour. The **consumer** (an agent like `lovelaice`, or Claude
  Code, or aegis, or any application) owns the cycle. See §2.
- **Not a RAG-over-documents box.** It builds a semi-structured knowledge graph
  with real semantic relationships and learns from use, rather than just
  indexing chunks for retrieval.

**The problem LETO solves** is NELL's problem (Never-Ending Language Learner,
Mitchell et al.): *how to maintain a long-term knowledge base that is always
getting better.* Where NELL grows a **global** knowledge base with **no task**,
LETO adds **task-relevant recall** and **usage-driven shaping** — and it does so
for both *what is* (facts) and *how things are done* (procedures).

Conceptually, LETO is where the loose ideas in Alex's ecosystem — **know-how**,
**skills**, and **soul** — get cemented and correctly conceptualized under
**ontology** (what is what) and **teleology** (what does what), as a solid,
reusable package.

The reference consumer, shipped as a **demo**, is a **never-ending learner à la
NELL**: an agent (built on `lovelaice`) that, given a topic, loops — web-search →
`ingest` the results → `settle`/`refactor` → repeat — continuously growing the
ontology (entities/relations) *and* teleology (procedures) about that topic. It
is the living proof of the "always improving" claim and of the boundary
principle: the **agent owns the never-ending loop**, LETO provides the
operations. See §8.7.

---

## 2. The boundary principle (the most important decision)

> **LETO = infrastructure + deterministic-ish LLM operations.**
> Every use of an LLM is a **single, explicit, well-structured prompt pass**
> hanging off a method call (`ingest`, `settle`, `refactor`, `recall`). LETO
> never runs an agentic multi-step loop.

The **consumer agent is the owner of the cycle**: ingest → review → maintain →
recall. LETO provides the operations; the agent decides when and how to call
them. This keeps LETO:

- **Testable** — each operation is a deterministic-ish pass with a fixed
  contract, not an open-ended agent.
- **Library-friendly** — you can call any operation in isolation.
- **Honest about its identity** — the heavy reasoning (planning, working-memory
  construction) lives in the consumer, not smuggled into the engine.

An LLM may appear at ingestion (to extract), during settlement (to summarize,
chunk, merge), and optionally at the output of recall (to synthesize a blob) —
always as one structured pass, never as an agent.

---

## 3. The three knowledge layers

LETO maintains **three layers** over the same substrate:

| Layer | Question | Content | Analogy |
|-------|----------|---------|---------|
| **Factual (ontological)** | *what is what* | entities + relations | the ontology / the "wiki" |
| **Procedural (teleological)** | *what does what / how* | procedures: goal → method → steps | know-how / skills |
| **Associative (Hebbian)** | *which path works under which intent* | learned, weighted, intent-conditioned links | long-term potentiation / habit |

The factual and procedural layers are **authored/extracted content** (markdown
notes). The associative layer is **learned structure** shaped by use — it is
distinct from, and layered on top of, the authored graph.

Two cross-cutting dimensions:

- **Settlement** (a maturity gradient, §6) tags every factual and procedural
  note. It says how well-settled a piece of knowledge is, and it travels in the
  answer so the consumer knows what is solid vs. tentative.
- **Weight** on associative edges (§7) says how reliable a learned navigation
  path is.

---

## 4. The substrate

The backend is a **folder of plain-text markdown notes, indexed in beaver**,
navigable by LETO *and* directly from outside (by hand, by other tools).

A **note** is:

- **Frontmatter (YAML):** `kind` (`entity` | `procedure`), `settlement` level,
  and typed attributes. This is machine-readable metadata.
- **Wikilinks + YAML relations:** the *implicit graph skeleton*. Rich relations
  between nodes are expressed as `[[wikilinks]]` and structured YAML fields.
- **Body (markdown prose):** where the **rich semantic knowledge lives**.
  Indexed semantically by beaver.

So the graph structure (skeleton) and the semantic content (bodies) coexist —
a **semi-structured knowledge graph**. The authored wikilink graph is the
*ontological truth*: clean, human-editable. The associative layer (§7) is
learned *habit* and lives in a **separate** beaver-backed weighted index, so it
never pollutes the authored graph.

**Beaver's roles:**

- Semantic index over note bodies (vector search for recall).
- Structured collections for the graph skeleton and for associative weights.
- IPC-safe persistence (it is the default local DB in this ecosystem).

> Beaver's vector indexing is numpy-only in this ecosystem (no compiled ANN
> deps). LETO must respect that constraint.

---

## 5. Operations (the engine surface, conceptual)

Each is an explicit method (library) and, later, an MCP tool (§8.6):

- **`ingest(input)`** — the single polymorphic door. `input` may be a full
  document *or* an agent's reflections *or* any text. LETO runs one structured
  LLM pass to extract **facts** (entities + relations) and **procedures**, and
  lands them as fresh, low-settlement notes/annotations.
- **`recall(query)`** — given any flow/query, return a **knowledge blob**: the
  relevant concepts (factual) + how-tos (procedural), each tagged with its
  settlement level. Baseline construction is deterministic (semantic search +
  one-hop graph expansion + associative boosts). An optional LLM synthesis pass
  can render the blob into prose. Retrieval is a **pluggable strategy** (§9).
- **`reinforce(recall, useful, useless)`** — feed back which nodes helped,
  updating the associative layer (§7).
- **`settle()` / `refactor()`** — consolidation: merge duplicates, mark/resolve
  contradictions, advance settlement, clean up. Consumer-triggered.
- **Navigation / CRUD primitives** — read a note, walk links, list by
  settlement, etc., so the consumer can inspect the KB directly.

---

## 6. The settlement gradient

Every factual/procedural note carries a **settlement level** — a Zettelkasten-
style maturity gradient (e.g. `fleeting → developing → established → permanent`;
exact levels TBD in the core spec). Properties:

- **Ingestion** creates notes at the lowest level.
- **Consolidation** (`settle`/`refactor`) polishes notes in phases and advances
  their level: dedup, merge, generalize, resolve or explicitly **mark**
  contradictions.
- **Contradictions are tolerated temporarily** and on purpose (as in LETO 1),
  to be crosschecked later rather than force-resolved on arrival.
- **Recall reports settlement**, so a consumer synthesizing an answer knows
  whether what it is standing on is settled or still tentative.

This is the same "settle over time via maintenance passes" pattern as Alex's
`soul` / `know-how` / zettel-candidate → evergreen promotion — here made a
first-class engine mechanism.

---

## 7. The associative layer (Hebbian, intent-conditioned)

A **third learning signal**, distinct from ingestion (adds content) and
consolidation (matures content): it **shapes the retrieval structure by use**.

- **Hebbian:** nodes that co-appear across useful recalls get their connecting
  associative edge **strengthened**; unhelpful ones **weakened**, and
  consistently unhelpful ones **pruned**.
- **Intent-conditioned:** edges are not global "X relates to Z" but
  *"under intent Y, from X it is worth going to Z"*. The query intent `Y` is
  bucketed (via embedding/cluster) so `X→Z under Y` does not pollute
  `X→W under Y'`. This is the semantics behind *"you're looking for Y and
  reached X, so go to Z — what's related to X under Y."*
- **Feedback is implicit + explicit:** co-occurrence accumulates passively; the
  consumer can also *say* a recall was good (`reinforce`) to correct a
  frequent-but-wrong attractor.
- **Separate substrate:** weights live in a beaver-backed index, distinct from
  the authored wikilink graph. Two planes: **truth** (authored ontology) vs.
  **habit** (learned associations).

Framing: this *is itself procedural/teleological knowledge* — **learned
navigation procedures**. Knowing how to move through the graph for a given goal
is a "how" learned from experience. It connects directly to the
episodic → consolidated arc in Beltrán's research (§11).

Effect over time: repeated queries converge **faster** along reinforced paths,
dead paths fade, and the graph self-organizes around actual usage.

---

## 8. Decomposition into sub-projects

LETO II is large. It is built as a sequence of sub-projects, each with its own
spec → plan → build. Dependency order, bottom-up:

1. **Core + note store** — note model (YAML schema, kinds, settlement),
   wikilink graph, beaver indexing, CRUD + navigation + semantic search.
   *(foundation)*
2. **Ingestion** — polymorphic input → one structured LLM extraction pass →
   factual + procedural notes. *(on 1)*
3. **Retrieval / knowledge-blob** — deterministic semantic + graph baseline,
   settlement-aware assembly, optional LLM synthesis, pluggable strategy
   interface. *(on 1)*
4. **Consolidation / settlement** — merge, contradictions, advance settlement,
   refactor. *(on 1)*
5. **Associative memory (recall reinforcement)** — the Hebbian, intent-
   conditioned layer + `reinforce`. *(on 1, 3)*
6. **MCP server surface** — exposes the operations to agents. *(on 1–5)*
7. **Never-ending learner demo** — a `lovelaice`-based agent that, given a
   topic, loops web-search → `ingest` → `settle` → repeat, growing the ontology
   + teleology of that topic without end (NELL-style, plus the teleological
   layer NELL lacks). Needs a web-search tool and an autonomous loop that live
   **in the agent, not in LETO**. Consumes LETO as a library (MCP surface
   optional for this demo). *(on 1–4; associative layer §8.5 and MCP §8.6 are
   enhancements, not prerequisites)*

The **library API** is not a sub-project; it is *how* 1–5 are called.

---

## 9. First vertical slice (VS1)

The thinnest end-to-end path that exercises the whole skeleton, driven through
the **library** (no MCP, no consolidation, no associative layer, no demo yet):

> `engine.ingest(text)` → extract a few facts + one procedure → write them as
> markdown notes (`frontmatter + settlement: fleeting`) into the folder, indexed
> in beaver → `engine.recall(query)` → return a blob with the relevant notes
> (semantic search + one-hop graph) and their settlement tags.

**Verifiable:** ingest known text → assert notes exist with the right shape →
`recall` a query → assert the blob contains the expected concepts.

**In scope for VS1:** core note store (subset of §8.1), minimal ingestion
(§8.2), minimal deterministic retrieval (§8.3).
**Out of scope for VS1:** consolidation (§8.4), associative layer (§8.5), MCP
(§8.6), demo (§8.7), LLM synthesis at output, intent conditioning.

Subsequent slices, roughly in order: consolidation/settlement → associative
layer → MCP surface → lovelaice demo.

---

## 10. Relationship to prior art

- **LETO 1 (RANLP 2019).** Carries over: ontologies as the shared currency,
  tagging with source/domain/reliability (now generalized to *settlement*),
  deliberate tolerance of temporary contradictions, the knowledge-discovery /
  merge idea. New in LETO II: the **procedural** and **associative** layers, a
  **plain-text + beaver** substrate (vs. OWL/Neo4j), **engine-not-application**
  framing, and **usage-driven** learning.
- **NELL.** Antecedent for never-ending accumulation and consolidation. LETO's
  differentiator is **task-relevant recall** and **usage-driven shaping** —
  NELL grows a global KB with no task; LETO builds the right active knowledge
  for a query and learns navigation from feedback. The §8.7 demo makes this
  explicit: it re-does NELL (never-ending web-driven accumulation) but adds the
  teleological layer and settlement gradient NELL never had.
- **Beltrán's "Progressive Research Arc"** (working-memory construction from
  semantic / episodic / consolidated stores, neuro-symbolic). LETO provides the
  **substrate and a baseline** working-memory construction; his thesis
  researches **better constructions** as a **pluggable retrieval strategy**
  (§9) on top of LETO — a natural home that does not block the engine.
- **Alex's ecosystem** (`know-how`, `skills`, `soul`, the vault). These are the
  intuition LETO formalizes: procedural + factual notes with a settlement
  gradient, maintained by explicit passes.

---

## 11. Open questions (to resolve in sub-project specs)

- **Settlement levels:** how many, named how, and the exact advancement rules.
- **Contradiction representation:** how a marked contradiction is stored and
  surfaced in recall.
- **Extraction contract:** the structured output of the ingestion LLM pass
  (entity/relation/procedure schema) and how entity boundaries are decided.
- **Intent bucketing:** how query intent `Y` is embedded/clustered for the
  associative layer.
- **Domain isolation:** LETO 1 isolated knowledge per domain; does LETO II keep
  per-domain folders/indexes, or a single graph with domain tags?
- **Concurrency:** beaver IPC safety when multiple consumers ingest/recall.
- **Repo transition:** how the rewrite lands over the existing `leto-mvp` code
  (clean-slate module tree; migration of nothing, or of the loader ideas).
- **AGENTS.md:** the repo currently has none; it should grow one as the rewrite
  establishes conventions.
