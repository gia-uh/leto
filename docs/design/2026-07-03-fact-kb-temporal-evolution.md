# Open problem — temporal evolution in the factual KB

**Status:** open problem / note-to-self (not scoped yet).
**Date:** 2026-07-03.
**Related:** the vision's factual/ontological layer (§3); consolidation v1
(`2026-07-03-leto-ii-consolidation.md`, which *defers* contradiction detection).
**Prior art (strong):** Francisco Ernesto Préstamo Bernárdez, *"GraphRAG
Bitemporal: Actualización dinámica de documentos y tratamiento de la
temporalidad"* — Trabajo de Diploma, U. de La Habana (MatCom), tutores Dr.
Yudivián Almeida Cruz + Dr. Alberto Fernández Oliva, 2026-06-12.
`github.com/fprestamo/graphrag`. (Read from the "Entrega tesis 25-26" Telegram
group via morse's new `download_media`.)

## The problem

LETO's factual layer models a fact as a **timeless note** with a settlement
gradient (`fleeting → developing → established`). Ingestion accumulates
provenance; consolidation merges duplicates and matures well-sourced notes.
Nothing in this model represents **how a fact changes over time**.

Francisco's thesis names the trichotomy LETO currently collapses into "merge":

1. **Evolution** — a fact was true, then stopped being true (the CEO changed;
   "Apple 1985" vs "Apple 2024" — same entity, very different state).
2. **Correction** — a fact was *never* true and is recognized as an error.
3. **Corroboration** — a new source confirms an existing fact.

LETO treats all three as one `settle()` outcome (merge / advance). Worse, its
**judge is atemporal**, so it over-merges an entity's distinct-in-time states or
merely-related entities — exactly the over-merge observed in the NELL smoke
(`arthur-scherbius` ← `enigma-machine`, `bletchley-park` ← `alan-turing`). And
**settlement rewards corroboration count, not recency** — a stale-but-often-
repeated fact can outrank a fresher correct one.

## BT-GRAPHRAG's answer (the blueprint to borrow from)

Francisco puts temporality **inside the indexing pipeline** (not a query-time
filter). Core pieces, each of which maps onto a LETO primitive:

- **Bitemporal quadruple per edge:** `Q(a) = (tᵥˢ, tᵥᵉ, t_tˢ, t_tᵉ)` — a
  *valid-time* interval `[tᵥˢ, tᵥᵉ]` (when the fact was true in the world) and a
  *transaction-time* interval `[t_tˢ, t_tᵉ]` (when the system believed it); `+∞`
  = still true / still believed. → **LETO:** give a note/claim these marks;
  today it has only untimed `sources`.
- **Derived epistemic states** (`active` / `in dispute` / `retracted`) computed
  from the quadruple, plus a source-count on the edge. → **LETO:** the
  source-count already exists (drives settlement); the epistemic state is new.
- **`as-of` queries + late-arrival documents:** reconstruct the graph as it was
  at a date; a document dated well after the fact triggers `as-of` logic so later
  corrections don't contaminate the past. → **LETO:** time-aware `recall`
  ("what is true now" vs "what was true at T").
- **Active conflict detection/resolution during indexing (ETCDR):** on each new
  edge, an LLM detects conflicts and picks one of 5 resolution strategies,
  updating the edge's temporal marks in place. → **LETO:** this is the deferred
  "contradiction detection" — but split into evolution/correction/corroboration.
- **Asymmetric cardinality classification (4 categories):** replaces a symmetric
  exclusive/non-exclusive flag; says *from which end* the exclusivity constraint
  applies, so conflict search is directed. → **LETO:** metadata on relation types.
- **Temporal entity resolution (CGER):** cosine pre-filter → LLM verification
  that **receives each entity's active period** and returns one of three
  verdicts — *same entity* / *distinct referent* / *temporal separation* (same
  referent, two temporally-distant states). → **LETO:** this is the direct fix
  for the over-merge. LETO's binary same-entity judge should become this
  **three-verdict, time-aware** judge so "Apple 1985"/"Apple 2024" are kept as
  linked-but-distinct states, not fused.

## Shape of a LETO answer (unscoped)

- Add **valid-time / assertion-time** to notes (bitemporal-lite), sourced from
  the document date where available.
- Replace the binary merge judge with a **three-verdict temporal judge**
  (same / distinct / temporal-separation) — also cures the atemporal over-merge.
- Make `recall` **as-of aware**; keep contradiction, correction, and evolution as
  distinct consolidation outcomes.
- The fact model likely needs the temporal fields *before* contradiction or
  temporal-evolution passes can be done well.

## Next step

Left as an open problem, but the design path is unusually clear thanks to
Francisco's thesis — read Ch. 2–3 in full (bitemporal formalization, CGER,
ETCDR, dual store) before scoping a LETO slice. Note the alignment: LETO ≈ a
markdown/beaver-substrate cousin of BT-GRAPHRAG; his bitemporal edge model and
three-verdict temporal entity resolution transfer almost directly.
