# Open problem — temporal evolution in the factual KB

**Status:** open problem / note-to-self (not scoped yet).
**Date:** 2026-07-03.
**Related:** the vision's factual/ontological layer (§3), consolidation v1
(`2026-07-03-leto-ii-consolidation.md`, which *defers* contradiction detection).
**External reference:** Francisco Préstamo's thesis — submitted 2026-06-14 in the
Telegram group *"Entrega tesis 25-26"* (flagged by Alex as relevant to this
problem; PDF not read here — morse has no media download).

## The problem

LETO's factual layer models a fact as a **timeless note** with a settlement
gradient (`fleeting → developing → established`). Ingestion accumulates
provenance; consolidation merges duplicates and matures well-sourced notes.
Nothing in this model represents **how a fact changes over time**.

Two distinct axes get conflated today and neither is handled:

1. **Contradiction** (already deferred): two notes assert conflicting facts *at
   the same time*. The v1 spec parks this ("mark a conflict, cap settlement").
2. **Temporal evolution** (this note): a single fact is **true over an interval
   and then superseded** — valid-time changes. Examples: "X is the director of
   Y" (true 2019–2023, then false); an entity's attributes that shift across
   sources published years apart; a procedure that was best-practice then and is
   deprecated now.

A never-ending learner (the NELL-style demo) makes this acute: it re-ingests the
same entities across time from sources of different vintages. With the current
model, the newer and older statements either (a) merge into one note that
silently overwrites the older truth, or (b) look like a contradiction — when in
fact **both were true, at different times**. Settlement (corroboration count)
can even *reward* a stale-but-often-repeated fact over a fresher correct one.

## Why it doesn't fit the current primitives

- **Settlement** measures *corroboration/maturity*, not *recency/validity*. A
  fact can be well-settled and out of date.
- **Merge** unions provenance and fuses bodies; it has no notion of "this clause
  superseded that clause as of date D."
- **Sources** carry a provenance id (URL) but no **valid-time** or
  **assertion-time** — so the KB can't order facts on a timeline.

## Shape of a possible answer (unscoped)

Candidate directions to evaluate later (not decisions):

- Give notes/claims a **valid-time interval** and/or an **as-of / assertion
  timestamp** (bitemporal-lite), sourced from the document's date where available.
- On re-ingest of the same entity, detect *evolution* vs *duplication* vs
  *contradiction* as three outcomes, not one merge.
- Let recall be **time-aware**: "what is true now" vs "what was true at T".
- Keep contradiction and temporal-evolution as **separate** consolidation passes
  (they have different repair semantics).

## Next step

Left as an open problem. Revisit alongside the deferred contradiction-detection
slice — they are adjacent but not the same, and the fact model likely needs the
temporal fields before either can be done well. Check Francisco's thesis for
prior art / an approach before designing.
