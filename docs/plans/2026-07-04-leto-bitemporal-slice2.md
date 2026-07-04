# LETO Bitemporal Queries — Slice 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the LETO store bitemporal query mechanics: a mechanically-derived `epistemic_state(slug, at)` (active / superseded / retracted), an `as_of(T)` reconstruction (what LETO believed-was-true at T), and an `active_notes(at)` filter — all zero-LLM.

**Architecture:** Builds directly on VS1's store. `epistemic_state` derives from the temporal fields (`valid_to`, `recorded_at`) plus incoming `supersedes` backlinks; `as_of`/`active_notes` filter `all_notes`. Timestamps are ISO-8601 strings compared lexicographically (a property of well-formed ISO-8601). No new storage — pure reads over what VS1 already persists.

**Tech Stack:** Python ≥3.13, `pydantic` v2, `beaver-db` (async), `pytest` + `pytest-asyncio`.

**Spec:** `docs/design/2026-07-04-leto-knowledge-model.md` §3 (temporal). Follows `2026-07-04-leto-knowledge-model-vs1.md`.

## Global Constraints

- **Zero LLM.** Derivations are mechanical; tests use no LLM/embedder.
- **`leto/store.py` is the only module importing `beaver`.** Async throughout.
- **Timestamps are ISO-8601 strings** (date or datetime), compared lexicographically. `valid_to = None` means INF (still true).
- **Epistemic precedence:** `SUPERSEDED` > `RETRACTED` > `ACTIVE`.
- **`as_of(T)` is bitemporal:** a note is in the as-of set iff it was **known by T** (`recorded_at <= T`) **and valid at T** (`valid_from <= T < valid_to`). This reconstructs LETO's belief state at T, so later corrections don't contaminate the past (Préstamo's as-of).
- **Supersession respects transaction-time:** a note is `SUPERSEDED` as of T only if a superseding note was itself known by T.
- **Commits:** conventional, one per task, to `main`. Trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. TDD.

## File Structure

- `leto/model.py` — add `EpistemicState` enum.
- `leto/store.py` — add `epistemic_state`, `as_of`, `active_notes` (module `NOW` already exists).
- `leto/__init__.py` — export `EpistemicState`.

---

### Task 1: `EpistemicState` + `store.epistemic_state(slug, at)`

**Files:**
- Modify: `leto/model.py`
- Modify: `leto/store.py`
- Modify: `tests/test_store.py` (append)

**Interfaces:**
- Consumes: `NoteStore.get`, `NoteStore.backlinks`, `EdgeType.SUPERSEDES`, `NOW` (store); `Note.valid_to`, `Note.recorded_at`.
- Produces:
  - `EpistemicState(str, Enum)`: `ACTIVE="active"`, `SUPERSEDED="superseded"`, `RETRACTED="retracted"`.
  - `async NoteStore.epistemic_state(slug: str, at: str | None = None) -> EpistemicState` (defaults `at` to `NOW()`; raises `ValueError` if the note is missing).

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`

```python
from leto.model import EpistemicState, EdgeType


async def test_epistemic_active_by_default(store):
    await store.put(_fact("a", "A"))
    assert await store.epistemic_state("a") == EpistemicState.ACTIVE


async def test_epistemic_retracted_when_valid_to_past(store):
    n = _fact("a", "A")
    n.valid_to = "2020-01-01"
    await store.put(n)
    assert await store.epistemic_state("a", at="2026-01-01") == EpistemicState.RETRACTED
    assert await store.epistemic_state("a", at="2019-01-01") == EpistemicState.ACTIVE


async def test_epistemic_superseded_respects_transaction_time(store):
    await store.put(_fact("old", "Old"))
    new = _fact("new", "New")
    new.recorded_at = "2026-06-01"
    await store.put(new)
    await store.link("new", "old", EdgeType.SUPERSEDES)   # new supersedes old
    assert await store.epistemic_state("old", at="2026-05-01") == EpistemicState.ACTIVE
    assert await store.epistemic_state("old", at="2026-07-01") == EpistemicState.SUPERSEDED
    assert await store.epistemic_state("new", at="2026-07-01") == EpistemicState.ACTIVE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Workspace/repos/leto && uv run pytest tests/test_store.py -q`
Expected: FAIL — `ImportError` for `EpistemicState` / `NoteStore` has no `epistemic_state`.

- [ ] **Step 3: Add `EpistemicState` to `leto/model.py`** (after the `Settlement` enum)

```python
class EpistemicState(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
```

- [ ] **Step 4: Add `epistemic_state` to `leto/store.py`** (before `close`)

Extend the model import at the top of `store.py`:

```python
from leto.model import (
    Edge, EdgeType, EpistemicState, Note, ORDERED_EDGES, edge_allowed, retrieval_key,
)
```

Add the method:

```python
    async def epistemic_state(self, slug: str, at: str | None = None) -> EpistemicState:
        at = at or NOW()
        note = await self.get(slug)
        if note is None:
            raise ValueError(f"note {slug!r} does not exist")
        # superseded: a superseding note (incoming supersedes edge) known by `at`
        for src in await self.backlinks(slug, EdgeType.SUPERSEDES):
            if (src.recorded_at or "") <= at:
                return EpistemicState.SUPERSEDED
        # retracted: its validity ended on/before `at`
        if note.valid_to is not None and note.valid_to <= at:
            return EpistemicState.RETRACTED
        return EpistemicState.ACTIVE
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add leto/model.py leto/store.py tests/test_store.py
git commit -m "feat(store): mechanically-derived epistemic_state (active/superseded/retracted)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `store.as_of(T)` + `store.active_notes(at)`

**Files:**
- Modify: `leto/store.py`
- Modify: `tests/test_store.py` (append)

**Interfaces:**
- Consumes: `NoteStore.all_notes`, `NoteStore.epistemic_state`, `NOW`.
- Produces:
  - `async NoteStore.as_of(at: str) -> list[Note]` — notes known **and** valid at `at`.
  - `async NoteStore.active_notes(at: str | None = None) -> list[Note]` — notes whose `epistemic_state(at)` is `ACTIVE`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`

```python
async def test_as_of_reconstructs_known_and_valid(store):
    n = _fact("x", "X")
    n.valid_from, n.valid_to, n.recorded_at = "2019-01-01", "2021-01-01", "2019-06-01"
    await store.put(n)
    assert "x" in [m.slug for m in await store.as_of("2020-01-01")]   # known + valid
    assert "x" not in [m.slug for m in await store.as_of("2018-01-01")]  # not yet known/valid
    assert "x" not in [m.slug for m in await store.as_of("2022-01-01")]  # no longer valid


async def test_active_notes_excludes_superseded(store):
    await store.put(_fact("old", "Old"))
    await store.put(_fact("new", "New"))
    await store.link("new", "old", EdgeType.SUPERSEDES)
    slugs = [m.slug for m in await store.active_notes()]
    assert "new" in slugs and "old" not in slugs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL — `NoteStore` has no `as_of` / `active_notes`.

- [ ] **Step 3: Add the methods** to `leto/store.py` (before `close`)

```python
    async def as_of(self, at: str) -> list[Note]:
        """Notes LETO both knew (recorded_at <= at) and that were valid
        (valid_from <= at < valid_to) at `at` — the belief state at that time."""
        out: list[Note] = []
        for note in await self.all_notes():
            known = (note.recorded_at or "") <= at
            started = (note.valid_from or "") <= at
            ended = note.valid_to is not None and note.valid_to <= at
            if known and started and not ended:
                out.append(note)
        return out

    async def active_notes(self, at: str | None = None) -> list[Note]:
        at = at or NOW()
        out: list[Note] = []
        for note in await self.all_notes():
            if await self.epistemic_state(note.slug, at) == EpistemicState.ACTIVE:
                out.append(note)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add leto/store.py tests/test_store.py
git commit -m "feat(store): as_of(T) belief-state reconstruction + active_notes filter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Export `EpistemicState` + full-suite green

**Files:**
- Modify: `leto/__init__.py`

**Interfaces:**
- Produces: `EpistemicState` in the package's public surface.

- [ ] **Step 1: Add `EpistemicState` to `leto/__init__.py`**

In the `from leto.model import (...)` block add `EpistemicState`, and add `"EpistemicState"` to `__all__`:

```python
from leto.model import (
    Edge, EdgeType, EpistemicState, ExperiencePayload, FactPayload, Kind, LAYER,
    Note, Outcome, ProcedurePayload, Settlement, edge_allowed, retrieval_key, slugify,
)
```

(and `"EpistemicState",` in `__all__`)

- [ ] **Step 2: Run the full suite**

Run: `cd ~/Workspace/repos/leto && uv run pytest -q`
Expected: all pass (model + markdown + store, including the new bitemporal tests).

- [ ] **Step 3: Verify the public API**

Run: `uv run python -c "import leto; print('EpistemicState' in leto.__all__)"`
Expected: `True`.

- [ ] **Step 4: Commit + push + release the lock**

```bash
git add leto/__init__.py
git commit -m "feat(leto): export EpistemicState

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin main
bin/ws-lock gc
```

---

## Self-Review

**Spec coverage (against `2026-07-04-leto-knowledge-model.md` §3):**
- valid-time / transaction-time fields → already in VS1 (`Note`); used here. ✓
- epistemic state (active/superseded/retracted) **derived mechanically** from time + `supersedes` edges → Task 1. ✓
- `as_of(T)` reconstruction → Task 2. ✓
- "default recall returns only active" → `active_notes` provides the mechanic (recall assembly itself is a follow-on spec). ✓
- supersession respects transaction-time (a superseding note must be known by T) → Task 1 test + impl. ✓

**Placeholder scan:** none.

**Type consistency:** `EpistemicState` defined in Task 1 (model), imported in store (Task 1) and exported (Task 3). `epistemic_state(slug, at=None)` signature consistent between Task 1 (def) and Task 2 (`active_notes` call). `as_of(at)` / `active_notes(at=None)` consistent with the export. Reuses VS1's `get`, `backlinks(slug, EdgeType.SUPERSEDES)`, `all_notes`, and `NOW` verbatim.
