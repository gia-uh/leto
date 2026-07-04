# LETO — Knowledge Model (nodes, edges, time) — Design

**Status:** design. **Date:** 2026-07-04.
**Grounds:** `2026-07-04-leto-substrate-vision.md` (zero-LLM, agent-driven
substrate) and `2026-07-03-fact-kb-temporal-evolution.md` (bitemporal prior art).

**Scope:** this spec defines only the **knowledge model** — node kinds + typed
payloads, the typed/ordered graph and its *enforced* invariants, and the
bitemporal dimension. The **tool surface (CLI ≡ MCP)**, the **recall assembly**,
and the **usage-learning (associative) layer** are follow-on specs that build on
this one. This is the foundation everything else inherits.

## 0. The mechanical / inferential boundary (recap)

LETO holds **zero LLM**. In this model that means LETO **stores, validates, and
derives** mechanically; the agent **infers**. Concretely:

| LETO (mechanical, deterministic) | Agent (linguistic inference) |
|---|---|
| store notes/edges; enforce invariants | extract notes from text |
| embed (local model) + index | decide two notes are the same |
| derive epistemic state from time + edges | decide valid-time / supersession |
| compute settlement eligibility (source count) | gate a settlement advance |
| answer `as_of(T)` | decide a note is really a rule (promote) |
| detect + surface candidates/violations | judge / merge / summarize |

## 1. Node model — uniform spine + typed payload

Every note shares a **spine** (what the graph, recall, settlement, temporal, and
maintenance machinery operate on). Each **kind** adds a typed **payload** with a
distinct **retrieval key** — the text LETO embeds for that kind, which is what
`recall` matches against.

```
Kind = "fact" | "procedure" | "experience"          # layers: fact < procedure < experience

Note (spine):
  slug: str                      # stable id (from title)
  kind: Kind
  title: str
  settlement: Settlement         # trust axis (§2)
  sources: list[str]             # provenance ids (dedup → distinct-source count)
  aliases: list[str]             # slugs merged away into this note
  valid_from: Timestamp          # valid-time start (§3); agent-supplied
  valid_to: Timestamp | INF      # valid-time end; INF = still true
  recorded_at: Timestamp         # transaction-time; LETO-stamped
  usage: Usage                   # {count, last_used} — fuel for the associative layer
  payload: FactPayload | ProcedurePayload | ExperiencePayload

FactPayload:        definition: str                 # retrieval key: title + definition
ProcedurePayload:   goal: str                        # retrieval key: goal  (steps are EDGES, §4)
ExperiencePayload:  situation: str                    # retrieval key: situation
                    action: str
                    outcome: "worked" | "failed"
                    lesson: str
```

The retrieval key is what makes the two typed recalls precise: `explain("what is
Y")` matches fact keys; `how_to("X")` matches procedure `goal`s and experience
`situation`s (not their solutions — so the match is on the problem, not the
answer).

**Markdown remains canonical.** A note serializes to a `.md` file: frontmatter =
the spine metadata (kind, settlement, sources, aliases, valid_from/to,
recorded_at, usage, and this note's outbound typed edges); body = the payload
rendered as sections (`## Definition`, `## Goal`, `## Situation / Action /
Outcome / Lesson`). Beaver holds the derived FTS + vector + graph indices.

## 2. Settlement — the trust axis (mechanical)

Unchanged in spirit: distinct-source count drives *eligibility*
(`fleeting → developing → established`, thresholds 2/3); the **agent gates** the
advance; `permanent` is human-only. Settlement answers "how corroborated is
this," and is **orthogonal** to time (§3): a fact can be `established` yet
`superseded`.

## 3. Time — bitemporal, from day one

Every note carries two independent time axes:

- **valid-time** `[valid_from, valid_to)` — when the fact is true in the world.
  `valid_to = INF` means "still true." **Agent-supplied** (from the source's date
  or its own inference); defaults to `[recorded_at, INF)`.
- **transaction-time** `recorded_at` — when LETO learned it. **LETO-stamped**
  from the system clock. (Kept single-valued for v1; a full transaction interval
  is a later refinement.)

**Epistemic state** — `active | superseded | retracted` — is **derived
mechanically** from the time fields plus `supersedes` edges (a note superseded by
a newer one is `superseded`; a note with `valid_to` in the past is not currently
true). LETO computes it; it never judges it.

`as_of(T)` queries reconstruct "what was known/true at T" by filtering on the two
axes. Default recall returns only `active` notes.

The **agent** owns temporal judgment (is this a contradiction, an evolution, or a
correction?) and expresses it via edges (`supersedes`, `contradicts`) and
valid-time. LETO stores, derives, and answers as-of — no inference.

## 4. Graph — typed/ordered edges, enforced invariants

Edges are **first-class, typed, and (where relevant) ordered** — not a flat slug
list. Ontology:

| edge | from → to | ordered | meaning |
|---|---|---|---|
| `relates_to` | fact→fact, exp→exp | no | generic association |
| `involves` | procedure→fact | no | the procedure uses this fact/entity |
| `step` | procedure→procedure | **yes** (`order`) | an ordered sub-step (itself a reusable procedure) |
| `depends_on` | procedure→procedure | no | prerequisite |
| `applied` | experience→procedure | no | this experience used that procedure (see `outcome`) |
| `about` | experience→fact | no | the experience concerns this fact |
| `follows` | experience→experience | no | temporal/causal succession |
| `supersedes` | same-kind | no | this note replaces that one (§3) |
| `contradicts` | same-kind | no | conflicts with that one (agent-flagged) |

(Aliases from a merge live in the alias dict + the note's `aliases` field, not as
graph edges. Cross-layer promotion provenance is recorded as note **metadata**
(`promoted_from: list[slug]`), not as an up-edge — see §5 — so the downstream
rule has **no exceptions**.)

**Layered downstream rule (ENFORCED).** Layers order as
`fact < procedure < experience`. A note of kind K may only author edges to kinds
**≤ K**. Reverse navigation ("which experiences use this fact") is **backlinks
computed** from the graph — never hand-authored. LETO **rejects** an up-edge.

**Invariants LETO enforces on every write** (violations → typed error +
suggested fix, never a silently broken graph):

1. **Edge direction** obeys the layered rule and the ontology's from→to kinds.
2. **Endpoints exist** — no dangling edges. Linking to a missing target is
   rejected with "create it first" (and the ready-to-run `remember` call).
3. **No cycles** in `step` / `depends_on` (a procedure can't be, transitively, a
   step of itself).
4. **Backlinks are derived, not stored** — the reverse of any edge is computed.
5. **Merge preserves all of the above atomically** (§5).

Edges live in the note's frontmatter (canonical) and are mirrored to beaver's
graph (`link(src, tgt, label=type, metadata={order})`); enforcement happens at
the write API before either is touched.

## 5. Maintenance operations (agent-driven, LETO-atomic)

- **Merge** — the agent supplies the decision (members + canonical
  title/payload); LETO commits atomically: pick survivor, union links + sources +
  aliases, redirect incoming edges, leave alias entries, delete absorbed,
  re-embed. All §4 invariants hold after commit.
- **Cross-layer promotion** — `promote(note, to=fact)` when the agent infers a
  recurring procedure/experience is really a rule (e.g. repeated
  `outcome=failed` experiences → a fact "X doesn't work"). LETO changes the kind,
  re-validates edges under the new layer (dropping any that would now be
  up-edges, since a fact can link to fewer kinds), and records the origin slugs
  in the new note's `promoted_from` **metadata** (not a graph edge — that would
  point up). Origin experiences may keep a downstream `about` edge to the new
  fact. Inference is the agent's; the mechanics are LETO's.

## 6. Recall shape (consequence of the model — implementation is a follow-on spec)

The model dictates what recall can assemble; here we fix the *shape*, not the
ranking (that + usage-learning is a later spec):

- `how_to(X)` **assembles a subgraph**, not a single note: the root procedure +
  its ordered `step` traversal (expanding sub-procedures) + `involves` facts +
  experience caveats (`applied` with `outcome=failed`). A composed, annotated
  plan.
- `explain(Y)` → the fact + its immediate neighborhood + epistemic state.
- Both default to `active`; `as_of(T)` reconstructs history.
- Results carry the spine's trust (settlement), currency (epistemic state),
  provenance (sources), and navigational backlinks.

## 7. Delta from the current implementation

Today: `NoteKind ∈ {entity, procedure}`, a flat `links: list[str]`, `body: str`,
settlement + sources + aliases, no time, no typed edges, injected LLM callables.
This spec changes: `kind` → `{fact, procedure, experience}` (rename
`entity`→`fact`); `body` → typed payloads with retrieval keys; `links` → typed/
ordered edges with enforced invariants; adds the bitemporal fields + derived
epistemic state + usage stats. (The LLM removal + tool surface land in their own
specs.) A migration/re-plan is out of scope here.

## 8. Out of scope (follow-on specs)

- Tool surface (CLI ≡ MCP, affordances, `init` self-bootstrap, failure feedback).
- Recall ranking + assembly implementation + the usage-learning associative layer.
- Removing the injected LLM callables from the engine (the substrate re-plan).
- Local embedder selection.

## 9. Open questions (small)

- Exact `Timestamp` representation (ISO string vs epoch) and `INF` sentinel —
  implementation detail; ISO strings + a `null`/`"INF"` sentinel is the leaning.
- Whether `contradicts` needs edge-level valid-time (probably not in v1 — note-
  level time suffices; revisit with the temporal-consolidation slice).
- Whether `usage` lives in the note frontmatter (canonical) or only in a beaver
  side-index (it's high-churn; a side-index may be cleaner). Leaning: beaver
  side-index, not frontmatter, to keep `.md` diffs stable.
