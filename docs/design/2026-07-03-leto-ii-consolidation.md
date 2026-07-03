# LETO II — Consolidation (v1) Design

**Status:** design — the second implementation slice (after VS1).
**Date:** 2026-07-03
**Grounds:** vision §8.4 (consolidation/settlement), §6 (settlement gradient), §3
(three layers). Builds on VS1 (`leto/model.py`, `markdown.py`, `store.py`,
`engine.py`).

> Consolidation is what makes LETO a *learner* and not a *hoarder*: as the same
> entity arrives under different titles from different sources, `settle()` fuses
> the duplicates into one canonical note, unions their provenance and links, and
> matures the note up the settlement gradient. This is the anti-NELL core.

## Scope

**In (v1):**
- **Entity resolution** — candidate duplicates via beaver hybrid search (vector
  ∪ FTS, RRF-reranked) → LLM judge (same entity? yes/no).
- **Merge-in-place** — an LLM pass fuses a confirmed cluster into one canonical
  note (rewrites body, unions links + provenance, redirects incoming edges,
  leaves aliases).
- **Settlement advancement** — hybrid: a note advances a level when it has
  ≥ threshold distinct corroborating sources **and** an LLM gate approves.

**Deferred (later slices):**
- Contradiction detection/marking (vision §6) — a clean fast-follow: the merge
  marks a conflict and caps settlement; not required for the demo.
- Procedural (teleological) consolidation — same candidate→judge→merge shape,
  but "same procedure" (by goal) and step-fusion semantics differ; own slice.
- `refactor()` — broader structural cleanup.
- Incremental/dirty-tracking of `settle()` scope (v1 scans the whole KB).

## 1. Substrate changes (embeddings + provenance enter)

- **`ingest` gains a source.** `Engine.ingest(text, source: str)` — `source` is
  a provenance id (for the demo, the URL). Every note is born with
  `sources=[source]`, `settlement=fleeting`.
- **Embeddings in ingest.** Each note is vectorized with an injected `embedder`
  and stored in beaver's vector index (`Document.embedding`). `NoteStore` gains
  `search_vector(vector, top_k)` alongside the existing `match` (FTS).
- **`Note` gains two fields:** `sources: list[str]` (provenance, unioned on
  merge) and `aliases: list[str]` (slugs merged away into this note).
- **Alias index.** A beaver `db.dict("aliases")` maps old-slug → canonical-slug
  for O(1) resolution; `NoteStore.get` follows aliases so external links to a
  merged-away slug still resolve.

## 2. The `settle()` pipeline

`Engine.settle()` runs a fixed sequence of deterministic-ish passes over the KB
(topic-scoped, small); idempotent. **Not** an agent loop — the consumer decides
*when* to call it.

1. **Blocking (candidates).** For each not-yet-consolidated note, gather
   `vector_hits = store.search_vector(embed(note))` and
   `keyword_hits = store.match(note.title + note.body)`, then fuse with beaver's
   built-in `rerank(vector_hits, keyword_hits, k=60)` (Reciprocal Rank Fusion).
   Top candidates (excluding self) become candidate pairs. Deterministic given
   the embedder.
2. **Judge (LLM).** For each candidate pair, `judge(a, b) -> bool` ("same
   entity?"). Confirmed-true pairs are unioned into clusters (union-find).
3. **Merge (LLM).** For each cluster of size ≥ 2, `merger(notes) -> MergedNote`
   produces the canonical title + body. The store then commits the merge (§5).
4. **Advance (hybrid).** For each surviving canonical note, if
   `len(set(note.sources)) >= threshold(next_level)` **and**
   `gate(note, next_level) -> True`, advance one level (§6).

`settle()` returns a `SettleReport` (clusters merged, notes promoted). Running it
again with no new ingestion finds no new candidates → no-op.

## 3. Interfaces (injected; lingo defaults; fakes in tests)

Consolidation logic lives in `leto/consolidate.py` (a `Consolidator`);
`Engine.settle()` delegates. Four injected dependencies, each a **direct
LLM/embedding pass, never an agent**:

- `Embedder = Callable[[str], list[float]]` — also used by `ingest`.
- `Judge = Callable[[Note, Note], bool]` — same entity?
- `Merger = Callable[[list[Note]], MergedNote]` — canonical title + body.
- `Gate = Callable[[Note, Settlement], bool]` — approve advancing to this level?

**Defaults (lingo-backed)** live in a separate module `leto/backends_lingo.py`,
each one a single structured pass via lingo's
`Engine.create[T: BaseModel](prompt) -> T` (Pydantic-typed output, incl. YAML
frontmatter generation). These backends are **not** unit-tested (non-
deterministic); they are smoke-tested manually.

**Testing:** the `Consolidator`/`Engine` logic is tested with **deterministic
fakes** — a keyword embedder, a title-stem judge, a concatenating merger, a
count-based gate. Zero real LLM/embedding calls in the test suite. (Tests are
the verification layer; they never depend on a real model.)

## 4. Data model & API

**`Note`** (additions to VS1): `sources: list[str] = []`, `aliases: list[str] = []`.

**`MergedNote`** (new): `title: str`, `body: str` — the merger's output; the
store derives the rest (slug, unioned links/sources, settlement).

**API:**
- `Engine.ingest(text: str, source: str) -> list[Note]` — **changes the VS1
  signature** (adds `source`). Each note: `sources=[source]`,
  `settlement=fleeting`, embedding indexed.
- `Engine.settle() -> SettleReport` — runs the §2 pipeline.
- `SettleReport` (new): `merged: list[MergeRecord]`, `promoted: list[str]`
  (canonical slugs advanced), where `MergeRecord` = `canonical: str`,
  `absorbed: list[str]`, `new_settlement: str | None`.
- `NoteStore` additions: store embedding in `put`; `search_vector(vector,
  top_k) -> list[tuple[Note, float]]`; alias dict + alias-following `get`;
  `redirect_edges(from_slug, to_slug)`; `delete(slug)`.

## 5. Merge canonicalization

Given a confirmed cluster and the merger's `MergedNote`:

1. **Choose the survivor slug** — highest settlement, then most sources, then
   lexicographically-first slug (deterministic tie-break).
2. **Build the canonical note** — survivor slug; merger's title + body; links =
   union of all members' links (minus self/aliases); sources = union of all
   members' sources; settlement = max of members' settlements (advancement in
   §6 is separate).
3. **Redirect incoming edges** — every graph edge pointing at an absorbed slug
   is relinked to the canonical slug (`store.redirect_edges`).
4. **Delete absorbed notes** — remove their `.md` file and beaver doc; write an
   alias entry `absorbed-slug → canonical-slug`; append absorbed slugs to
   `canonical.aliases`.
5. **Persist** the canonical note (`store.put`), re-embedding its merged body.

## 6. Settlement advancement

- **Thresholds (distinct sources):** `developing` = 2, `established` = 3.
  `fleeting` is the birth level; `permanent` is **human-only** (the machine
  tops out at `established`, matching the Evergreen discipline — the human
  promotes to permanent).
- **Rule (hybrid):** a note advances to the next level iff
  `len(set(note.sources)) >= threshold(next_level)` **and**
  `gate(note, next_level) -> True`. The count is necessary but not sufficient;
  the LLM gate vetoes premature promotion of incoherent/incomplete notes.
- Advancement runs after merge in the same `settle()` pass, one level per pass
  (a note can climb multiple levels across repeated `settle()` calls as sources
  accumulate).

## 7. Testing strategy

- **Unit (deterministic fakes):**
  - Blocking finds the obvious duplicate cluster ("Alan Turing" / "Turing,
    Alan") and excludes unrelated notes ("Water").
  - Merge produces one canonical note; absorbed slugs deleted; `aliases`
    populated; `store.get(old_slug)` resolves to canonical; links + sources
    unioned; incoming edges redirected.
  - Advancement: a note with 2 distinct sources + gate→True becomes
    `developing`; with gate→False stays; `permanent` never set by the machine.
  - Idempotency: a second `settle()` with no new ingestion returns an empty
    report.
- **Smoke (manual, real lingo):** the lingo backends judge/merge/gate on a small
  real example. Not in the automated suite.

## 8. Open questions (pin at plan spike)

- Exact `rerank` import path/signature in beaver-db 2.0rc4 (guide says
  `from beaver.collections import rerank`; confirm) and the `search_vector`
  call for the vector index (beaver `search(vector, top_k)`).
- Exact `lingo.Engine.create` call shape (prompt/model args, engine
  construction) for the backend defaults.
- Embedding model behind the lingo/default embedder (dimensionality, provider).
- Candidate cap per note (top-N after rerank) and self-exclusion details.

## 9. Out of scope (restated)

Contradiction detection/marking, procedural-note consolidation, `refactor()`,
incremental `settle()` scoping, and the associative (Hebbian) layer (§8.5) — all
later slices.
