# LETO Knowledge Model — VS1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The thinnest end-to-end slice of the new zero-LLM substrate: typed notes (fact / procedure / experience) with typed payloads, markdown round-trip, an async beaver-backed store, and a **typed graph whose invariants LETO enforces** (downstream direction + endpoints-exist), with computed backlinks.

**Architecture:** Rebuild `model.py` (typed spine + per-layer payloads + edge ontology), `markdown.py` (frontmatter-canonical round-trip), and `store.py` (async `AsyncBeaverDB`; put/get/match/search_vector/all_notes; `link` with enforced invariants; neighbors/backlinks by edge type). Temporal *fields* are stored from day one; their query semantics (epistemic state, `as_of`) and merge/promote are named follow-on slices. The LLM-orchestrated layer (`engine`, `consolidate`, `backends_lingo`, `nell`) is **removed** — it is incompatible with the typed model and superseded by the tool-surface spec.

**Tech Stack:** Python ≥3.13, `uv`, `pydantic` v2, `python-frontmatter`, `beaver-db>=2.0.0rc4` (async API), `pytest` + `pytest-asyncio`.

**Spec:** `docs/design/2026-07-04-leto-knowledge-model.md` (grounded in `2026-07-04-leto-substrate-vision.md`).

## Global Constraints

- **Zero LLM in LETO.** Everything here is mechanical + deterministic; tests use no LLM/embedder (a fixed local vectorizer fake where a vector is needed).
- **`leto/store.py` is the only module that imports `beaver`.** Async throughout (`await NoteStore.open(...)`; `AsyncBeaverDB`).
- **Markdown is canonical for parsing via frontmatter; the body is a generated human-readable view** (not parsed back). Beaver holds derived FTS + vector + graph indices.
- **Layers order `fact < procedure < experience`.** A note of kind K authors edges only to kinds ≤ K. LETO **rejects** violations with a typed error. Backlinks are computed, never stored.
- **Enforced graph invariants (this slice):** edge (from_kind, type, to_kind) must be in the allowed set; both endpoints must exist; no self-edge. (No-cycles for `step`/`depends_on`, merge, promote, and bitemporal queries are follow-on slices.)
- **Temporal fields exist from day one:** every note carries `valid_from`, `valid_to` (None = INF, still true), `recorded_at` (LETO-stamped). Query semantics deferred.
- **Commits:** conventional, one per task, straight to `main`. Trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. TDD: failing test → minimal impl → green → commit.
- **ws-lock** `repos/leto` before starting; `gc` at the end.

## File Structure

- `leto/model.py` — rewrite: `Kind`, `Settlement`, `Outcome`, payloads, `EdgeType`, `Edge`, `Note` (spine+payload+temporal), `slugify`, `retrieval_key`, `EDGE_RULES`, `LAYER`.
- `leto/markdown.py` — rewrite: `note_to_markdown` / `note_from_markdown` (frontmatter-canonical).
- `leto/store.py` — rewrite (async): `NoteStore.open`, `put`, `get`, `all_notes`, `match`, `search_vector`, `link`, `neighbors`, `backlinks`, `close`.
- `leto/__init__.py` — export the model + store surface.
- **Removed:** `leto/engine.py`, `leto/consolidate.py`, `leto/backends_lingo.py`, `examples/nell.py`, `examples/test_nell.py`, `tests/test_engine.py`, `tests/test_consolidate.py`, `tests/test_vs1_end_to_end.py`, `tests/test_consolidation_end_to_end.py`.

### Confirmed beaver async API (grounded)

`db = AsyncBeaverDB(path); await db.connect()`. `docs = db.docs(name, model=)`; `await docs.index(document=Document(id=, body=))`, `await docs.search(query, on=[...]) -> list[ScoredDocument]` (`.document.body`, `.score`), `await docs.drop(id)`. `vec = db.vectors(name)`; `await vec.set(id, vector)`, `await vec.near(vector, k=) -> list[VectorItem]` (`.id`, `.score`), `await vec.delete(id)`. `g = db.graph(name)`; `await g.link(src, tgt, label=, metadata=)`, `g.children(src, label=) -> AsyncIterator[str]`, `g.parents(tgt, label=) -> AsyncIterator[str]`, `await g.unlink(...)`. `d = db.dict(name)`; `await d.set(k,v)`, `await d.fetch(k, default)`. `await db.close()`.

---

### Task 1: Remove the superseded LLM-orchestration layer

The new typed model is incompatible with the LLM-orchestrated `engine`/`consolidate`/`backends_lingo` (they use `ExtractedItem`, `Note.body`, flat `links`, `NoteKind.entity`, injected `judge/merger/gate`). Per the substrate vision, that layer is discarded (recall + consolidation return as the agent-driven tool surface, a follow-on spec). Remove it and its tests so the tree rebuilds cleanly. **This deletes currently-working code — it is intentional and flagged for review.**

**Files:**
- Delete: `leto/engine.py`, `leto/consolidate.py`, `leto/backends_lingo.py`, `examples/nell.py`, `examples/test_nell.py`, `tests/test_engine.py`, `tests/test_consolidate.py`, `tests/test_vs1_end_to_end.py`, `tests/test_consolidation_end_to_end.py`.

- [ ] **Step 1: Remove the modules and their tests**

```bash
cd ~/Workspace/repos/leto
git rm leto/engine.py leto/consolidate.py leto/backends_lingo.py \
       examples/nell.py examples/test_nell.py \
       tests/test_engine.py tests/test_consolidate.py \
       tests/test_vs1_end_to_end.py tests/test_consolidation_end_to_end.py
```

- [ ] **Step 2: Neutralize `leto/__init__.py` temporarily** (model rewrite in Task 2 restores exports)

Replace `leto/__init__.py` with a minimal placeholder so the package imports while `model`/`store` are rebuilt:

```python
"""LETO — Learning Engine Through Ontologies (zero-LLM substrate)."""

__version__ = "0.0.1"
```

- [ ] **Step 3: Confirm the remaining tests still collect** (model/markdown/store still reference the OLD model and will be rewritten next)

Run: `cd ~/Workspace/repos/leto && uv run pytest -q tests/test_model.py tests/test_markdown.py tests/test_store.py --co -q`
Expected: collection succeeds for the three files (they still import the old `leto.model`/`leto.store`, which exist until Task 2/4). If any of the deleted-module tests were referenced, none remain.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor!: remove the LLM-orchestrated layer (engine/consolidate/backends/nell)

Superseded by the zero-LLM substrate vision; incompatible with the typed
knowledge model. Recall + consolidation return as the agent-driven tool surface
(follow-on spec).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: New `model.py` — typed spine, payloads, edge ontology

**Files:**
- Rewrite: `leto/model.py`
- Rewrite: `tests/test_model.py`

**Interfaces:**
- Produces (used everywhere downstream):
  - `Kind(str, Enum)`: `FACT="fact"`, `PROCEDURE="procedure"`, `EXPERIENCE="experience"`.
  - `LAYER: dict[Kind, int]` = `{FACT:0, PROCEDURE:1, EXPERIENCE:2}`.
  - `Settlement(str, Enum)`: `FLEETING/DEVELOPING/ESTABLISHED/PERMANENT`.
  - `Outcome(str, Enum)`: `WORKED="worked"`, `FAILED="failed"`.
  - `FactPayload(definition: str = "")`, `ProcedurePayload(goal: str = "")`, `ExperiencePayload(situation: str = "", action: str = "", outcome: Outcome = Outcome.WORKED, lesson: str = "")`.
  - `EdgeType(str, Enum)`: `RELATES_TO/INVOLVES/STEP/DEPENDS_ON/APPLIED/ABOUT/FOLLOWS/SUPERSEDES/CONTRADICTS` (values = lowercase names).
  - `EDGE_RULES: dict[EdgeType, tuple[set[Kind], set[Kind]]]` — allowed (from-kinds, to-kinds) per type.
  - `ORDERED_EDGES: set[EdgeType]` = `{EdgeType.STEP}`.
  - `Edge(target: str, type: EdgeType, order: int | None = None)`.
  - `Note(slug, kind, title, settlement=FLEETING, sources=[], aliases=[], valid_from: str | None=None, valid_to: str | None=None, recorded_at: str | None=None, promoted_from=[], edges: list[Edge]=[], payload)` with a validator that `payload` matches `kind`.
  - `slugify(text) -> str`.
  - `retrieval_key(note: Note) -> str`.
  - `edge_allowed(from_kind, type, to_kind) -> bool`.

- [ ] **Step 1: Write the failing test** `tests/test_model.py`

```python
import pytest

from leto.model import (
    Kind, Settlement, Outcome, EdgeType, Edge, Note, LAYER,
    FactPayload, ProcedurePayload, ExperiencePayload,
    slugify, retrieval_key, edge_allowed,
)


def test_slugify():
    assert slugify("  Alan Turing!  ") == "alan-turing"


def test_layers_order_fact_below_experience():
    assert LAYER[Kind.FACT] < LAYER[Kind.PROCEDURE] < LAYER[Kind.EXPERIENCE]


def test_note_requires_matching_payload():
    Note(slug="turing", kind=Kind.FACT, title="Alan Turing",
         payload=FactPayload(definition="A mathematician."))
    with pytest.raises(ValueError):
        Note(slug="x", kind=Kind.FACT, title="X",
             payload=ProcedurePayload(goal="do x"))


def test_retrieval_key_per_kind():
    fact = Note(slug="y", kind=Kind.FACT, title="Y",
                payload=FactPayload(definition="the def"))
    proc = Note(slug="do-x", kind=Kind.PROCEDURE, title="Do X",
                payload=ProcedurePayload(goal="accomplish x"))
    exp = Note(slug="e", kind=Kind.EXPERIENCE, title="E",
               payload=ExperiencePayload(situation="hit a wall", action="tried z",
                                         outcome=Outcome.FAILED, lesson="z is bad"))
    assert retrieval_key(fact) == "Y. the def"
    assert retrieval_key(proc) == "accomplish x"
    assert retrieval_key(exp) == "hit a wall"


def test_edge_direction_rules():
    # procedure -> fact (involves) allowed; fact -> procedure (up) forbidden
    assert edge_allowed(Kind.PROCEDURE, EdgeType.INVOLVES, Kind.FACT)
    assert not edge_allowed(Kind.FACT, EdgeType.INVOLVES, Kind.PROCEDURE)
    # experience -> procedure (applied) allowed
    assert edge_allowed(Kind.EXPERIENCE, EdgeType.APPLIED, Kind.PROCEDURE)
    # step is procedure -> procedure only
    assert edge_allowed(Kind.PROCEDURE, EdgeType.STEP, Kind.PROCEDURE)
    assert not edge_allowed(Kind.EXPERIENCE, EdgeType.STEP, Kind.PROCEDURE)
    # relates_to same-kind (fact-fact, exp-exp), not fact-exp
    assert edge_allowed(Kind.FACT, EdgeType.RELATES_TO, Kind.FACT)
    assert not edge_allowed(Kind.FACT, EdgeType.RELATES_TO, Kind.EXPERIENCE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_model.py -q`
Expected: FAIL — `ImportError` (new names not yet defined).

- [ ] **Step 3: Write the implementation** `leto/model.py`

```python
from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Kind(str, Enum):
    FACT = "fact"
    PROCEDURE = "procedure"
    EXPERIENCE = "experience"


LAYER: dict[Kind, int] = {Kind.FACT: 0, Kind.PROCEDURE: 1, Kind.EXPERIENCE: 2}


class Settlement(str, Enum):
    FLEETING = "fleeting"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    PERMANENT = "permanent"


class Outcome(str, Enum):
    WORKED = "worked"
    FAILED = "failed"


class FactPayload(BaseModel):
    definition: str = ""


class ProcedurePayload(BaseModel):
    goal: str = ""


class ExperiencePayload(BaseModel):
    situation: str = ""
    action: str = ""
    outcome: Outcome = Outcome.WORKED
    lesson: str = ""


_PAYLOAD_FOR: dict[Kind, type] = {
    Kind.FACT: FactPayload,
    Kind.PROCEDURE: ProcedurePayload,
    Kind.EXPERIENCE: ExperiencePayload,
}


class EdgeType(str, Enum):
    RELATES_TO = "relates_to"
    INVOLVES = "involves"
    STEP = "step"
    DEPENDS_ON = "depends_on"
    APPLIED = "applied"
    ABOUT = "about"
    FOLLOWS = "follows"
    SUPERSEDES = "supersedes"
    CONTRADICTS = "contradicts"


# (allowed from-kinds, allowed to-kinds) per edge type. All respect the
# downstream rule (to-layer <= from-layer); it is also asserted in edge_allowed.
EDGE_RULES: dict[EdgeType, tuple[set[Kind], set[Kind]]] = {
    EdgeType.RELATES_TO: ({Kind.FACT, Kind.EXPERIENCE}, {Kind.FACT, Kind.EXPERIENCE}),
    EdgeType.INVOLVES: ({Kind.PROCEDURE}, {Kind.FACT}),
    EdgeType.STEP: ({Kind.PROCEDURE}, {Kind.PROCEDURE}),
    EdgeType.DEPENDS_ON: ({Kind.PROCEDURE}, {Kind.PROCEDURE}),
    EdgeType.APPLIED: ({Kind.EXPERIENCE}, {Kind.PROCEDURE}),
    EdgeType.ABOUT: ({Kind.EXPERIENCE}, {Kind.FACT}),
    EdgeType.FOLLOWS: ({Kind.EXPERIENCE}, {Kind.EXPERIENCE}),
    EdgeType.SUPERSEDES: ({Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE},
                          {Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE}),
    EdgeType.CONTRADICTS: ({Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE},
                           {Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE}),
}

ORDERED_EDGES: set[EdgeType] = {EdgeType.STEP}

# supersedes/contradicts are same-kind (checked in edge_allowed).
_SAME_KIND_ONLY: set[EdgeType] = {EdgeType.SUPERSEDES, EdgeType.CONTRADICTS}


def edge_allowed(from_kind: Kind, type: EdgeType, to_kind: Kind) -> bool:
    froms, tos = EDGE_RULES[type]
    if from_kind not in froms or to_kind not in tos:
        return False
    if type in _SAME_KIND_ONLY and from_kind is not to_kind:
        return False
    # relates_to is same-kind (fact-fact or exp-exp), never cross
    if type is EdgeType.RELATES_TO and from_kind is not to_kind:
        return False
    # downstream rule: never point up a layer
    return LAYER[to_kind] <= LAYER[from_kind]


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return s.strip("-")


class Edge(BaseModel):
    target: str
    type: EdgeType
    order: int | None = None


class Note(BaseModel):
    slug: str
    kind: Kind
    title: str
    settlement: Settlement = Settlement.FLEETING
    sources: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    valid_from: str | None = None
    valid_to: str | None = None          # None = INF (still true)
    recorded_at: str | None = None       # stamped by the store on write
    promoted_from: list[str] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    payload: FactPayload | ProcedurePayload | ExperiencePayload

    @model_validator(mode="after")
    def _payload_matches_kind(self) -> "Note":
        if not isinstance(self.payload, _PAYLOAD_FOR[self.kind]):
            raise ValueError(
                f"payload {type(self.payload).__name__} does not match kind {self.kind}")
        return self


def retrieval_key(note: Note) -> str:
    if note.kind is Kind.FACT:
        return f"{note.title}. {note.payload.definition}".strip()
    if note.kind is Kind.PROCEDURE:
        return note.payload.goal or note.title
    return note.payload.situation or note.title   # experience
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_model.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add leto/model.py tests/test_model.py
git commit -m "feat(model): typed knowledge model — kinds, payloads, edge ontology, retrieval keys

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `markdown.py` — frontmatter-canonical round-trip

Frontmatter carries the full structured note (spine + payload + edges); the body is a generated human-readable view and is **not** parsed back.

**Files:**
- Rewrite: `leto/markdown.py`
- Rewrite: `tests/test_markdown.py`

**Interfaces:**
- Consumes: `Note`, `Edge`, `Kind`, `Settlement`, payloads (`leto.model`).
- Produces: `note_to_markdown(note: Note) -> str`; `note_from_markdown(text: str, slug: str) -> Note`.

- [ ] **Step 1: Write the failing test** `tests/test_markdown.py`

```python
from leto.model import (
    Kind, Settlement, Outcome, Edge, EdgeType, Note,
    FactPayload, ProcedurePayload, ExperiencePayload,
)
from leto.markdown import note_to_markdown, note_from_markdown


def test_fact_roundtrips_via_frontmatter():
    note = Note(
        slug="alan-turing", kind=Kind.FACT, title="Alan Turing",
        settlement=Settlement.DEVELOPING, sources=["https://a", "https://b"],
        aliases=["turing-alan"], valid_from="2019-01-01", recorded_at="2026-07-04",
        edges=[Edge(target="computer-science", type=EdgeType.RELATES_TO)],
        payload=FactPayload(definition="A mathematician who founded CS."))
    back = note_from_markdown(note_to_markdown(note), slug="alan-turing")
    assert back == note


def test_experience_roundtrips_with_ordered_steps():
    note = Note(
        slug="break-enigma", kind=Kind.EXPERIENCE, title="Breaking Enigma",
        edges=[],
        payload=ExperiencePayload(situation="ciphertext only", action="crib attack",
                                  outcome=Outcome.WORKED, lesson="cribs help"))
    back = note_from_markdown(note_to_markdown(note), slug="break-enigma")
    assert back == note


def test_body_is_human_readable_view():
    note = Note(slug="do-x", kind=Kind.PROCEDURE, title="Do X",
                payload=ProcedurePayload(goal="accomplish x"))
    text = note_to_markdown(note)
    assert text.startswith("---")
    assert "# Do X" in text
    assert "accomplish x" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_markdown.py -q`
Expected: FAIL — new `model` names / round-trip mismatch.

- [ ] **Step 3: Write the implementation** `leto/markdown.py`

```python
from __future__ import annotations

import frontmatter

from leto.model import (
    Edge, ExperiencePayload, FactPayload, Kind, Note, ProcedurePayload, Settlement,
)

_PAYLOAD_FOR = {
    Kind.FACT: FactPayload,
    Kind.PROCEDURE: ProcedurePayload,
    Kind.EXPERIENCE: ExperiencePayload,
}


def _render_body(note: Note) -> str:
    """A human-readable view of the note. Not parsed back — frontmatter is
    canonical."""
    lines = [f"# {note.title}", ""]
    p = note.payload
    if note.kind is Kind.FACT:
        lines.append(p.definition)
    elif note.kind is Kind.PROCEDURE:
        lines += [f"**Goal:** {p.goal}"]
    else:  # experience
        lines += [
            f"**Situation:** {p.situation}", "",
            f"**Action:** {p.action}", "",
            f"**Outcome:** {p.outcome.value}", "",
            f"**Lesson:** {p.lesson}",
        ]
    return "\n".join(lines).strip()


def note_to_markdown(note: Note) -> str:
    post = frontmatter.Post(
        _render_body(note),
        kind=note.kind.value,
        title=note.title,
        settlement=note.settlement.value,
        sources=list(note.sources),
        aliases=list(note.aliases),
        valid_from=note.valid_from,
        valid_to=note.valid_to,
        recorded_at=note.recorded_at,
        promoted_from=list(note.promoted_from),
        payload=note.payload.model_dump(mode="json"),
        edges=[e.model_dump(mode="json") for e in note.edges],
    )
    return frontmatter.dumps(post)


def note_from_markdown(text: str, slug: str) -> Note:
    post = frontmatter.loads(text)
    kind = Kind(post["kind"])
    payload = _PAYLOAD_FOR[kind](**(post.get("payload") or {}))
    return Note(
        slug=slug,
        kind=kind,
        title=post["title"],
        settlement=Settlement(post.get("settlement", "fleeting")),
        sources=list(post.get("sources", []) or []),
        aliases=list(post.get("aliases", []) or []),
        valid_from=post.get("valid_from"),
        valid_to=post.get("valid_to"),
        recorded_at=post.get("recorded_at"),
        promoted_from=list(post.get("promoted_from", []) or []),
        edges=[Edge(**e) for e in (post.get("edges", []) or [])],
        payload=payload,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_markdown.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add leto/markdown.py tests/test_markdown.py
git commit -m "feat(markdown): frontmatter-canonical round-trip for typed notes + edges

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `store.py` — async open / put / get / all_notes

`put` writes the canonical `.md`, stamps `recorded_at` (and defaults `valid_from` to it), FTS-indexes the retrieval key, and stores the embedding if given. `get` follows aliases.

**Files:**
- Rewrite: `leto/store.py`
- Rewrite: `tests/test_store.py`

**Interfaces:**
- Consumes: `Note`, `retrieval_key`, `note_to_markdown`/`note_from_markdown`; `AsyncBeaverDB`, `Document`.
- Produces:
  - `NoteStore(folder, db_path)` + `@classmethod async open(folder, db_path) -> NoteStore`.
  - `async put(note, embedding: list[float] | None = None) -> Note` (returns the stored note, with `recorded_at`/`valid_from` filled).
  - `async get(slug) -> Note | None` (alias-following).
  - `async all_notes() -> list[Note]` (sorted by slug).
  - `async close()`.
  - A module constant `NOW: Callable[[], str]` (ISO, overridable in tests).

- [ ] **Step 1: Write the failing test** `tests/test_store.py`

```python
import pytest
import pytest_asyncio

from leto.model import Kind, Note, FactPayload
from leto.store import NoteStore


@pytest_asyncio.fixture
async def store(tmp_path):
    s = await NoteStore.open(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield s
    await s.close()


def _fact(slug, title, definition=""):
    return Note(slug=slug, kind=Kind.FACT, title=title,
                payload=FactPayload(definition=definition))


async def test_put_stamps_recorded_at_and_defaults_valid_from(store):
    stored = await store.put(_fact("water", "Water", "H2O."))
    assert stored.recorded_at is not None
    assert stored.valid_from == stored.recorded_at


async def test_get_reads_note_back(store):
    await store.put(_fact("water", "Water", "H2O."))
    got = await store.get("water")
    assert got.title == "Water" and got.payload.definition == "H2O."
    assert await store.get("missing") is None


async def test_all_notes_sorted(store):
    await store.put(_fact("water", "Water"))
    await store.put(_fact("alan-turing", "Alan Turing"))
    assert [n.slug for n in await store.all_notes()] == ["alan-turing", "water"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL — new `NoteStore.open` / model.

- [ ] **Step 3: Write the implementation** `leto/store.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from beaver import AsyncBeaverDB, Document
from pydantic import BaseModel

from leto.markdown import note_from_markdown, note_to_markdown
from leto.model import Note, retrieval_key


def NOW() -> str:
    """ISO-8601 UTC timestamp. Overridable in tests via monkeypatch."""
    return datetime.now(timezone.utc).isoformat()


class NoteDoc(BaseModel):
    slug: str
    key: str          # the retrieval key (FTS target)
    kind: str


class NoteStore:
    def __init__(self, folder: str | Path, db_path: str | Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self._db: AsyncBeaverDB | None = None

    @classmethod
    async def open(cls, folder: str | Path, db_path: str | Path) -> "NoteStore":
        self = cls(folder, db_path)
        self._db = AsyncBeaverDB(self._db_path)
        await self._db.connect()
        self._docs = self._db.docs("notes", model=NoteDoc)
        self._vectors = self._db.vectors("embeddings")
        self._graph = self._db.graph("edges")
        self._aliases = self._db.dict("aliases")
        return self

    async def put(self, note: Note, embedding: list[float] | None = None) -> Note:
        if note.recorded_at is None:
            note.recorded_at = NOW()
        if note.valid_from is None:
            note.valid_from = note.recorded_at
        (self.folder / f"{note.slug}.md").write_text(
            note_to_markdown(note), encoding="utf-8")
        await self._docs.index(document=Document(
            id=note.slug,
            body=NoteDoc(slug=note.slug, key=retrieval_key(note), kind=note.kind.value)))
        if embedding is not None:
            await self._vectors.set(note.slug, embedding)
        return note

    async def get(self, slug: str) -> Note | None:
        path = self.folder / f"{slug}.md"
        if path.exists():
            return note_from_markdown(path.read_text(encoding="utf-8"), slug)
        canonical = await self._aliases.fetch(slug, None)
        if canonical and canonical != slug:
            return await self.get(canonical)
        return None

    async def all_notes(self) -> list[Note]:
        out = []
        for path in sorted(self.folder.glob("*.md")):
            note = await self.get(path.stem)
            if note is not None:
                out.append(note)
        return out

    async def close(self) -> None:
        await self._db.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add leto/store.py tests/test_store.py
git commit -m "feat(store): async NoteStore open/put/get/all_notes with recorded_at stamping

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `store.py` — FTS `match` + `search_vector`

**Files:**
- Modify: `leto/store.py`
- Modify: `tests/test_store.py` (append)

**Interfaces:**
- Produces:
  - `async match(query, top_k=5) -> list[tuple[Note, float]]` (FTS over the retrieval key).
  - `async search_vector(vector, top_k=5) -> list[tuple[Note, float]]`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`

```python
async def test_match_finds_by_retrieval_key(store):
    await store.put(_fact("alan-turing", "Alan Turing", "a mathematician"))
    await store.put(_fact("water", "Water", "a liquid"))
    hits = await store.match("mathematician", top_k=5)
    slugs = [n.slug for n, _ in hits]
    assert "alan-turing" in slugs and "water" not in slugs


async def test_search_vector_ranks_by_nearness(store):
    await store.put(_fact("a", "A", "x"), embedding=[1.0, 0.0, 0.0])
    await store.put(_fact("b", "B", "y"), embedding=[0.0, 1.0, 0.0])
    hits = await store.search_vector([0.9, 0.1, 0.0], top_k=2)
    assert hits[0][0].slug == "a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL — `NoteStore` has no `match`.

- [ ] **Step 3: Add the methods** to `leto/store.py` (before `close`)

```python
    async def match(self, query: str, top_k: int = 5) -> list[tuple[Note, float]]:
        results = await self._docs.search(query, on=["key"])
        out = []
        for scored in results[:top_k]:
            note = await self.get(scored.document.body.slug)
            if note is not None:
                out.append((note, scored.score))
        return out

    async def search_vector(
        self, vector: list[float], top_k: int = 5
    ) -> list[tuple[Note, float]]:
        out = []
        for item in await self._vectors.near(vector, k=top_k):
            note = await self.get(item.id)
            if note is not None:
                out.append((note, item.score))
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add leto/store.py tests/test_store.py
git commit -m "feat(store): FTS match + vector search over retrieval keys

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `store.py` — enforced `link` + `neighbors` + `backlinks`

`link` validates every invariant before writing (allowed triple / downstream direction, both endpoints exist, no self-edge). It persists the edge on the source note's frontmatter **and** mirrors it to the beaver graph. `neighbors`/`backlinks` traverse by edge type.

**Files:**
- Modify: `leto/store.py`
- Modify: `tests/test_store.py` (append)

**Interfaces:**
- Consumes: `Edge`, `EdgeType`, `edge_allowed`, `ORDERED_EDGES` (`leto.model`).
- Produces:
  - `async link(source_slug, target_slug, type: EdgeType, order: int | None = None) -> None` — raises `ValueError` on any invariant violation.
  - `async neighbors(slug, type: EdgeType | None = None) -> list[Note]` (outbound).
  - `async backlinks(slug, type: EdgeType | None = None) -> list[Note]` (inbound, computed).

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`

```python
from leto.model import EdgeType, ProcedurePayload


def _proc(slug, title, goal=""):
    return Note(slug=slug, kind=Kind.PROCEDURE, title=title,
                payload=ProcedurePayload(goal=goal))


async def test_link_persists_and_neighbors_backlinks(store):
    await store.put(_fact("cs", "Computer Science", "study of computation"))
    await store.put(_proc("do-cs", "Do CS", "compute"))
    await store.link("do-cs", "cs", EdgeType.INVOLVES)          # procedure -> fact
    assert [n.slug for n in await store.neighbors("do-cs")] == ["cs"]
    assert [n.slug for n in await store.backlinks("cs")] == ["do-cs"]
    # the edge is persisted on the source note's frontmatter
    again = await store.get("do-cs")
    assert again.edges and again.edges[0].target == "cs"


async def test_link_rejects_up_edge(store):
    await store.put(_fact("cs", "Computer Science"))
    await store.put(_proc("do-cs", "Do CS"))
    with pytest.raises(ValueError):
        await store.link("cs", "do-cs", EdgeType.INVOLVES)      # fact -> procedure (up)


async def test_link_rejects_missing_endpoint_and_self(store):
    await store.put(_proc("do-cs", "Do CS"))
    with pytest.raises(ValueError):
        await store.link("do-cs", "ghost", EdgeType.DEPENDS_ON)  # missing target
    with pytest.raises(ValueError):
        await store.link("do-cs", "do-cs", EdgeType.DEPENDS_ON)  # self
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL — `NoteStore` has no `link`.

- [ ] **Step 3: Add the methods** to `leto/store.py`

Add the import at the top of `store.py`:

```python
from leto.model import Note, retrieval_key, Edge, EdgeType, edge_allowed, ORDERED_EDGES
```

Add the methods (before `close`):

```python
    async def link(self, source_slug: str, target_slug: str, type: EdgeType,
                   order: int | None = None) -> None:
        if source_slug == target_slug:
            raise ValueError(f"self-edge not allowed on {source_slug!r}")
        source = await self.get(source_slug)
        target = await self.get(target_slug)
        if source is None:
            raise ValueError(f"source note {source_slug!r} does not exist")
        if target is None:
            raise ValueError(
                f"target note {target_slug!r} does not exist — create it first "
                f"(leto remember ...)")
        if not edge_allowed(source.kind, type, target.kind):
            raise ValueError(
                f"edge {source.kind.value} -{type.value}-> {target.kind.value} "
                f"is not allowed (check direction/ontology)")
        if type not in ORDERED_EDGES:
            order = None
        # persist on the source note (canonical) if not already present
        if not any(e.target == target.slug and e.type == type for e in source.edges):
            source.edges.append(Edge(target=target.slug, type=type, order=order))
            await self.put(source)
        # mirror to the graph index
        await self._graph.link(source.slug, target.slug, label=type.value,
                               metadata={"order": order})

    async def neighbors(self, slug: str, type: EdgeType | None = None) -> list[Note]:
        labels = [type.value] if type else [t.value for t in EdgeType]
        seen, out = set(), []
        for label in labels:
            async for target in self._graph.children(slug, label=label):
                if target not in seen:
                    seen.add(target)
                    note = await self.get(target)
                    if note is not None:
                        out.append(note)
        return out

    async def backlinks(self, slug: str, type: EdgeType | None = None) -> list[Note]:
        labels = [type.value] if type else [t.value for t in EdgeType]
        seen, out = set(), []
        for label in labels:
            async for source in self._graph.parents(slug, label=label):
                if source not in seen:
                    seen.add(source)
                    note = await self.get(source)
                    if note is not None:
                        out.append(note)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add leto/store.py tests/test_store.py
git commit -m "feat(store): enforced typed link + neighbors/backlinks by edge type

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Public API + full-suite green

**Files:**
- Rewrite: `leto/__init__.py`

**Interfaces:**
- Produces: the package export surface for the substrate.

- [ ] **Step 1: Write `leto/__init__.py`**

```python
"""LETO — Learning Engine Through Ontologies (zero-LLM knowledge substrate)."""

from leto.model import (
    Edge, EdgeType, ExperiencePayload, FactPayload, Kind, LAYER, Note, Outcome,
    ProcedurePayload, Settlement, edge_allowed, retrieval_key, slugify,
)
from leto.store import NoteStore

__version__ = "0.0.1"

__all__ = [
    "Kind", "Settlement", "Outcome", "Note", "Edge", "EdgeType", "LAYER",
    "FactPayload", "ProcedurePayload", "ExperiencePayload",
    "slugify", "retrieval_key", "edge_allowed", "NoteStore", "__version__",
]
```

- [ ] **Step 2: Run the full suite**

Run: `cd ~/Workspace/repos/leto && uv run pytest -q`
Expected: all pass (model + markdown + store). No references to removed modules.

- [ ] **Step 3: Verify the public API imports**

Run: `uv run python -c "import leto; print(sorted(leto.__all__))"`
Expected: prints the export list, no ImportError.

- [ ] **Step 4: Commit + release the lock**

```bash
git add leto/__init__.py
git commit -m "feat(leto): export the zero-LLM substrate surface (model + store)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin main
bin/ws-lock gc
```

---

## Follow-on slices (named, not in this plan)

- **Slice 2 — bitemporal queries:** `epistemic_state(slug)` (derived from `supersedes` backlinks + `valid_to`); `as_of(T)` filtering; recall default = active.
- **Slice 3 — maintenance:** atomic `merge(members, canonical)` (survivor selection, union edges/sources/aliases, redirect incoming edges, delete + alias, re-embed); `promote(slug, to_kind, ...)` with `promoted_from` metadata; `step`/`depends_on` cycle rejection.
- **Follow-on specs:** the CLI ≡ MCP tool surface with affordances + `init` self-bootstrap; recall assembly (`how_to` subgraph, `explain`); the usage-learning associative layer; the local embedder.

## Self-Review

**Spec coverage (against `2026-07-04-leto-knowledge-model.md`):**
- §1 node model (spine + typed payloads + retrieval key) → Task 2. ✓
- §2 settlement → field present (Task 2); advancement is follow-on (mechanical eligibility lives with merge/gate — noted). ✓ (field in-model)
- §3 temporal fields (valid_from/to, recorded_at) → Task 2 (fields) + Task 4 (recorded_at stamp, valid_from default). Epistemic state + as_of → Slice 2 (explicitly deferred). ✓
- §4 typed/ordered edges + enforced invariants (direction, endpoints, no self) → Task 2 (ontology) + Task 6 (enforcement). No-cycles → Slice 3 (deferred). Backlinks derived → Task 6. ✓
- §5 merge + promotion → Slice 3 (deferred). ✓ (out of VS1)
- §6 recall shape → follow-on spec. ✓ (out of VS1)
- §0 mechanical/inferential boundary → honored: everything here is mechanical, no LLM, tests use a fake vector only. ✓

**Placeholder scan:** none. Deferrals are explicit named slices, not TODOs.

**Type consistency:** `Kind/Settlement/Outcome/EdgeType/Edge/Note/payloads/slugify/retrieval_key/edge_allowed/LAYER/ORDERED_EDGES` defined in Task 2 and consumed unchanged in Tasks 3/6/7. `NoteStore` methods (`open/put/get/all_notes/match/search_vector/link/neighbors/backlinks/close`) consistent across Tasks 4–7. `NoteDoc.key` (retrieval-key FTS field) is written in Task 4's `put` and searched in Task 5's `match`. `note_to_markdown`/`note_from_markdown` signatures match between Task 3 and Task 4's store.
