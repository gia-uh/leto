# LETO II — Consolidation (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make LETO a *learner*: `settle()` fuses duplicate entity notes into one canonical note (union-find over an LLM judge), unions their provenance + links, redirects incoming edges, leaves aliases, and matures notes up the settlement gradient by a hybrid (distinct-source-count **and** LLM gate) rule.

**Architecture:** Consolidation logic lives in a new `leto/consolidate.py` (`Consolidator`); `Engine.settle()` delegates to it. Four dependencies are injected as **sync callables** (`Embedder`, `Judge`, `Merger`, `Gate`) — never agents. `NoteStore` (the only module that touches beaver) gains a vector index (a separate `db.vectors` collection), an alias dict, alias-following `get`, `redirect_edges`, `delete`, and `all_notes`. Tests use deterministic fakes; zero real LLM/embedding calls. The lingo-backed defaults live in `leto/backends_lingo.py` and are **not** unit-tested.

**Tech Stack:** Python ≥3.13, `uv`, `pydantic` v2, `python-frontmatter`, `beaver-db>=2.0.0rc4` (installed: 2.0rc5), `pytest`. Optional extra: `lingo-ai` (for the default backends only).

**Spec:** `docs/design/2026-07-03-leto-ii-consolidation.md`. Builds on VS1 (`docs/plans/2026-07-03-leto-ii-vs1.md`).

## Reality corrections vs the spec (confirmed against installed beaver 2.0rc5 + lingo-ai 2.1.0)

The spec's §2/§8 open questions are resolved here — three assumptions in the spec are wrong against the shipped code and are corrected in this plan:

1. **`beaver` has no `rerank` / no `beaver.collections`.** RRF fusion is implemented as a pure function `leto.consolidate.rerank(*rankings, k=60)` over ranked id-lists. This is *better* than leaning on a library call: it is deterministic and unit-tested (Task 7).
2. **`beaver.Document` is `{id, body}` only — no `embedding` field.** Embeddings are stored in a **separate** vector collection `db.vectors("embeddings")`: `.set(id, vector)`, `.near(vector, k) -> list[VectorItem]` (each with `.id`, `.score`), `.delete(id)`. `NoteStore.search_vector` wraps `.near`.
3. **lingo (`lingo-ai`) `Engine.create` is async** with signature `async create[T](self, context: Context, model: type[T], *instructions) -> T`, and `Embedder.embed` is async too. The injected LETO interfaces are **sync** callables, so `backends_lingo.py` bridges async→sync (`asyncio.run` per one-shot call). lingo is **not** installed in the leto venv — it becomes an optional extra `[project.optional-dependencies] llm`.

Confirmed sync-facade calls (via beaver's `BeaverBridge` portal — all materialize async iterators to lists):
- `docs.search(query, on=["title","text"]) -> list[ScoredDocument]` (`.document.body.slug`, `.score`; score is bm25-style and may be negative — fine for RRF, which ranks by order).
- `docs.index(document=Document(id=, body=NoteDoc(...)))`, `docs.drop(slug)`, `docs.get(id)`.
- `vectors.set(id, vector)`, `vectors.near(vector, k) -> list[VectorItem]`, `vectors.delete(id)`.
- `graph.link(src, tgt, label=)`, `graph.children(src, label=)`, `graph.parents(tgt, label=)`, `graph.unlink(src, tgt, label=)`.
- `dict.set(k, v)`, `dict.fetch(k, default)`.

## Global Constraints

- **Python ≥ 3.13**, managed with `uv`. Package name: `leto`. `[tool.uv] prerelease = "allow"` (beaver is a pre-release).
- **`leto/store.py` is the ONLY module that imports `beaver`.** All beaver access goes through `NoteStore`. This isolates the RC churn — including the corrections above.
- **No agent loop.** Every LLM/embedding use is an explicit injected sync pass (`Embedder`, `Judge`, `Merger`, `Gate`). **Tests NEVER call a real LLM or embedding model** — they inject deterministic fakes. Tests are the verification layer; they never depend on a real model.
- **The `.md` file is canonical**; beaver holds derived indices (FTS + vectors + graph + alias dict).
- **Settlement thresholds (distinct sources):** `developing` = 2, `established` = 3. `fleeting` is the birth level. `permanent` is **human-only** — the machine tops out at `established` and never sets `permanent`.
- **Advancement rule (hybrid):** advance to next level iff `len(set(note.sources)) >= threshold(next)` **AND** `gate(note, next) -> True`. One level per `settle()` pass.
- **Candidate cap:** at most **5** candidate partners per note after RRF fusion (excluding self). (Resolves spec §8.)
- **`backends_lingo.py` is NOT unit-tested** (non-deterministic). It is smoke-tested manually.
- **Commits:** conventional commits, one per task, straight to `main`. Author trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **TDD:** failing test first, minimal implementation, green, commit.
- **Workspace lock:** before starting, `bin/ws-lock acquire repos/leto --desc "leto consolidation v1"`; `bin/ws-lock gc` at the end (release is pid-scoped).

---

### Task 1: Spike verification (pin the corrected beaver + lingo APIs)

The corrections above were confirmed during planning. This task **re-verifies** them in the executor's environment before any code depends on them (beaver is a moving RC). Throwaway; nothing committed.

**Files:**
- Create (throwaway): `spike_consolidate.py` (delete before finishing).

**Interfaces:**
- Produces: confirmation that `vectors.near`, `graph.parents`/`unlink`, `dict.fetch`, `docs.drop`, and `docs.search` behave as the code in Tasks 4–6 assumes. If any differ, adjust only the `# beaver:`-marked lines in `store.py`.

- [ ] **Step 1: Write the spike** `spike_consolidate.py`

```python
import tempfile, os
from pydantic import BaseModel
from beaver import BeaverDB, Document


class NoteDoc(BaseModel):
    slug: str
    title: str
    text: str


tmp = tempfile.mkdtemp()
db = BeaverDB(os.path.join(tmp, "spike.db"))

docs = db.docs("notes", model=NoteDoc)
docs.index(document=Document(id="alan-turing", body=NoteDoc(
    slug="alan-turing", title="Alan Turing", text="mathematician computer science")))
docs.index(document=Document(id="water", body=NoteDoc(
    slug="water", title="Water", text="liquid hydrogen oxygen")))

print("== FTS ==")
for s in docs.search("mathematician", on=["title", "text"]):
    print("  ", s.document.body.slug, s.score)

print("== vectors (separate collection; Document has NO embedding field) ==")
vec = db.vectors("emb")
vec.set("alan-turing", [1.0, 0.0, 0.0])
vec.set("water", [0.0, 1.0, 0.0])
for it in vec.near([0.9, 0.1, 0.0], k=2):
    print("  ", it.id, it.score)
vec.delete("water")
print("  after delete count:", vec.count())

print("== graph parents/unlink ==")
g = db.graph("links")
g.link("alan-turing", "computer-science", label="relates_to")
g.link("bletchley", "computer-science", label="relates_to")
print("  parents:", list(g.parents("computer-science", label="relates_to")))
g.unlink("alan-turing", "computer-science", label="relates_to")
print("  after unlink:", list(g.parents("computer-science", label="relates_to")))

print("== dict + docs.drop ==")
d = db.dict("aliases")
d.set("turing-alan", "alan-turing")
print("  fetch:", d.fetch("turing-alan", None), "| missing:", d.fetch("nope", None))
docs.drop("water")
print("  docs count after drop:", docs.count())

db.close()
print("OK")
```

- [ ] **Step 2: Run the spike**

Run: `uv run python spike_consolidate.py`
Expected: prints `alan-turing` as top FTS + top vector hit, `parents` shrinks to `['bletchley']` after unlink, alias `fetch` returns `alan-turing` then `None`, counts decrement, ends `OK`.

If any call name/shape differs, note it — Tasks 4–6 use exactly these forms in `NoteStore`.

- [ ] **Step 3: Delete the spike (do not commit)**

```bash
rm spike_consolidate.py
```

No commit for this task.

---

### Task 2: Model additions (sources, aliases, merge + report types)

**Files:**
- Modify: `leto/model.py`
- Test: `tests/test_model.py` (append)

**Interfaces:**
- Consumes: existing `Note`, `Settlement` from `leto.model`.
- Produces (used by later tasks):
  - `Note.sources: list[str] = []`, `Note.aliases: list[str] = []` (both `Field(default_factory=list)`).
  - `MergedNote(BaseModel)`: `title: str`, `body: str`.
  - `MergeRecord(BaseModel)`: `canonical: str`, `absorbed: list[str] = []`, `new_settlement: str | None = None`.
  - `SettleReport(BaseModel)`: `merged: list[MergeRecord] = []`, `promoted: list[str] = []`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_model.py`

```python
def test_note_has_empty_sources_and_aliases_by_default():
    from leto.model import Note, NoteKind
    n = Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing")
    assert n.sources == []
    assert n.aliases == []


def test_merge_and_report_types_construct():
    from leto.model import MergedNote, MergeRecord, SettleReport
    m = MergedNote(title="Alan Turing", body="A mathematician.")
    assert m.title == "Alan Turing"
    rec = MergeRecord(canonical="alan-turing", absorbed=["turing-alan"],
                      new_settlement="fleeting")
    report = SettleReport(merged=[rec], promoted=["alan-turing"])
    assert report.merged[0].absorbed == ["turing-alan"]
    assert report.promoted == ["alan-turing"]
    empty = SettleReport()
    assert empty.merged == [] and empty.promoted == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_model.py -q`
Expected: FAIL with `ImportError: cannot import name 'MergedNote'` (and the `sources` assertion would also fail).

- [ ] **Step 3: Write the implementation** — edit `leto/model.py`

Add `sources` and `aliases` to `Note` (leave the other fields unchanged):

```python
class Note(BaseModel):
    slug: str
    kind: NoteKind
    title: str
    body: str = ""
    settlement: Settlement = Settlement.FLEETING
    links: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
```

Append the new types at the end of the module:

```python
class MergedNote(BaseModel):
    title: str
    body: str


class MergeRecord(BaseModel):
    canonical: str
    absorbed: list[str] = Field(default_factory=list)
    new_settlement: str | None = None


class SettleReport(BaseModel):
    merged: list[MergeRecord] = Field(default_factory=list)
    promoted: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_model.py -q`
Expected: all model tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/model.py tests/test_model.py
git commit -m "feat(model): note sources/aliases + merge & settle-report types

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Markdown round-trip for sources + aliases

`sources` and `aliases` join the YAML frontmatter so the `.md` file stays the canonical carrier of provenance and merge history.

**Files:**
- Modify: `leto/markdown.py`
- Test: `tests/test_markdown.py` (append)

**Interfaces:**
- Consumes: `Note` with `sources`/`aliases` (Task 2).
- Produces: `note_to_markdown` writes `sources:` + `aliases:`; `note_from_markdown` reads them back (defaulting to `[]`).

- [ ] **Step 1: Write the failing test** — append to `tests/test_markdown.py`

```python
def test_roundtrip_preserves_sources_and_aliases():
    from leto.model import Note, NoteKind, Settlement
    from leto.markdown import note_to_markdown, note_from_markdown
    note = Note(
        slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
        body="A mathematician.", settlement=Settlement.DEVELOPING,
        links=["computer-science"],
        sources=["https://a", "https://b"],
        aliases=["turing-alan"],
    )
    back = note_from_markdown(note_to_markdown(note), slug="alan-turing")
    assert back == note


def test_missing_sources_and_aliases_default_to_empty():
    from leto.markdown import note_from_markdown
    text = "---\nkind: entity\ntitle: Water\nsettlement: fleeting\nlinks: []\n---\nH2O."
    note = note_from_markdown(text, slug="water")
    assert note.sources == []
    assert note.aliases == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_markdown.py -q`
Expected: FAIL — round-trip mismatch (`sources`/`aliases` dropped).

- [ ] **Step 3: Write the implementation** — edit `leto/markdown.py`

```python
def note_to_markdown(note: Note) -> str:
    post = frontmatter.Post(
        note.body,
        kind=note.kind.value,
        title=note.title,
        settlement=note.settlement.value,
        links=list(note.links),
        sources=list(note.sources),
        aliases=list(note.aliases),
    )
    return frontmatter.dumps(post)


def note_from_markdown(text: str, slug: str) -> Note:
    post = frontmatter.loads(text)
    return Note(
        slug=slug,
        kind=NoteKind(post["kind"]),
        title=post["title"],
        body=post.content,
        settlement=Settlement(post.get("settlement", "fleeting")),
        links=list(post.get("links", []) or []),
        sources=list(post.get("sources", []) or []),
        aliases=list(post.get("aliases", []) or []),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_markdown.py -q`
Expected: all markdown tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/markdown.py tests/test_markdown.py
git commit -m "feat(markdown): round-trip sources + aliases frontmatter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Store — vector index + `search_vector` + `all_notes`

`NoteStore` gains a separate beaver vector collection. `put` optionally stores an embedding; `search_vector` queries it; `all_notes` enumerates the KB (needed by blocking). `put`'s `embedding` defaults to `None` so VS1's FTS-only tests keep passing.

**Files:**
- Modify: `leto/store.py`
- Test: `tests/test_store.py` (append)

**Interfaces:**
- Consumes: `beaver.BeaverDB`, `Note`. Uses the sync calls confirmed in Task 1.
- Produces:
  - `NoteStore.put(note: Note, embedding: list[float] | None = None) -> None` (signature extended; existing callers unaffected).
  - `NoteStore.search_vector(vector: list[float], top_k: int = 5) -> list[tuple[Note, float]]`.
  - `NoteStore.all_notes() -> list[Note]` (sorted by slug).

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`

```python
def test_search_vector_ranks_by_nearness(store):
    store.put(Note(slug="a", kind=NoteKind.ENTITY, title="A", body="x"),
              embedding=[1.0, 0.0, 0.0])
    store.put(Note(slug="b", kind=NoteKind.ENTITY, title="B", body="y"),
              embedding=[0.0, 1.0, 0.0])
    hits = store.search_vector([0.9, 0.1, 0.0], top_k=2)
    assert hits[0][0].slug == "a"


def test_all_notes_enumerates_sorted(store):
    store.put(Note(slug="water", kind=NoteKind.ENTITY, title="Water"))
    store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing"))
    assert [n.slug for n in store.all_notes()] == ["alan-turing", "water"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL with `AttributeError: 'NoteStore' object has no attribute 'search_vector'`.

- [ ] **Step 3: Write the implementation** — edit `leto/store.py`

Add the vector collection in `__init__` (after the graph line):

```python
        self._vectors = self._db.vectors("embeddings")        # beaver: vector index
```

Extend `put` (add the `embedding` param and the vector write; keep the file/FTS/graph body unchanged):

```python
    def put(self, note: Note, embedding: list[float] | None = None) -> None:
        (self.folder / f"{note.slug}.md").write_text(
            note_to_markdown(note), encoding="utf-8"
        )
        self._docs.index(                                     # beaver: FTS index
            document=Document(
                id=note.slug,
                body=NoteDoc(
                    slug=note.slug,
                    title=note.title,
                    text=note.body,
                    kind=note.kind.value,
                    settlement=note.settlement.value,
                ),
            )
        )
        if embedding is not None:
            self._vectors.set(note.slug, embedding)           # beaver: vector set
        for target in note.links:
            if (self.folder / f"{target}.md").exists():
                self._graph.link(note.slug, target, label="relates_to")  # beaver: edge
```

Add the two new methods:

```python
    def search_vector(
        self, vector: list[float], top_k: int = 5
    ) -> list[tuple[Note, float]]:
        out: list[tuple[Note, float]] = []
        for item in self._vectors.near(vector, k=top_k):      # beaver: vector near
            note = self.get(item.id)
            if note is not None:
                out.append((note, item.score))
        return out

    def all_notes(self) -> list[Note]:
        out: list[Note] = []
        for path in sorted(self.folder.glob("*.md")):
            note = self.get(path.stem)
            if note is not None:
                out.append(note)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all store tests pass (old FTS/graph tests still green — `put` default `embedding=None`).

- [ ] **Step 5: Commit**

```bash
git add leto/store.py tests/test_store.py
git commit -m "feat(store): vector index (search_vector) + all_notes enumeration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Store — alias dict, alias-following `get`, `delete`, `set_alias`

Merged-away slugs must still resolve so external links don't dangle. `get` follows the alias dict when no `.md` file exists. `delete` removes a note's file + FTS doc + vector. `set_alias` records `old -> canonical`.

**Files:**
- Modify: `leto/store.py`
- Test: `tests/test_store.py` (append)

**Interfaces:**
- Produces:
  - `NoteStore.set_alias(old_slug: str, canonical_slug: str) -> None`.
  - `NoteStore.get` now follows aliases (unchanged signature).
  - `NoteStore.delete(slug: str) -> None` (removes file, FTS doc, vector).

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`

```python
def test_delete_removes_file_and_get_returns_none(store, tmp_path):
    store.put(Note(slug="water", kind=NoteKind.ENTITY, title="Water", body="H2O"),
              embedding=[1.0, 0.0])
    store.delete("water")
    assert not (tmp_path / "notes" / "water.md").exists()
    assert store.get("water") is None


def test_get_follows_alias_to_canonical(store):
    store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                   body="Founder."))
    store.set_alias("turing-alan", "alan-turing")
    resolved = store.get("turing-alan")
    assert resolved is not None
    assert resolved.slug == "alan-turing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL with `AttributeError: 'NoteStore' object has no attribute 'set_alias'`.

- [ ] **Step 3: Write the implementation** — edit `leto/store.py`

Add the alias dict in `__init__` (after the vectors line):

```python
        self._aliases = self._db.dict("aliases")              # beaver: alias map
```

Replace `get` with the alias-following version:

```python
    def get(self, slug: str) -> Note | None:
        path = self.folder / f"{slug}.md"
        if path.exists():
            return note_from_markdown(path.read_text(encoding="utf-8"), slug)
        canonical = self._aliases.fetch(slug, None)            # beaver: alias fetch
        if canonical and canonical != slug:
            return self.get(canonical)
        return None
```

Add the two new methods:

```python
    def set_alias(self, old_slug: str, canonical_slug: str) -> None:
        self._aliases.set(old_slug, canonical_slug)            # beaver: alias set

    def delete(self, slug: str) -> None:
        path = self.folder / f"{slug}.md"
        if path.exists():
            path.unlink()
        self._docs.drop(slug)                                  # beaver: drop doc
        self._vectors.delete(slug)                             # beaver: drop vector
```

> Note: in the consolidation flow, `delete` is only ever called on notes that were ingested with an embedding, so `_vectors.delete` always has a target. The `delete` test above puts *with* an embedding for the same reason.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all store tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/store.py tests/test_store.py
git commit -m "feat(store): alias dict + alias-following get + delete

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Store — `redirect_edges`

When a note is absorbed, every incoming edge is relinked to the canonical slug (spec §5.3). Outgoing edges of the canonical are re-created by `put` from its unioned `links`, so `redirect_edges` handles **incoming** edges only.

**Files:**
- Modify: `leto/store.py`
- Test: `tests/test_store.py` (append)

**Interfaces:**
- Produces: `NoteStore.redirect_edges(from_slug: str, to_slug: str) -> None`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_store.py`

```python
def test_redirect_edges_relinks_incoming_to_canonical(store):
    # x -> turing-alan ; after redirect, x -> alan-turing, not turing-alan
    store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing"))
    store.put(Note(slug="turing-alan", kind=NoteKind.ENTITY, title="Turing, Alan"))
    store.put(Note(slug="x", kind=NoteKind.ENTITY, title="X",
                   links=["turing-alan"]))
    store.redirect_edges("turing-alan", "alan-turing")
    assert [n.slug for n in store.neighbors("x")] == ["alan-turing"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL with `AttributeError: 'NoteStore' object has no attribute 'redirect_edges'`.

- [ ] **Step 3: Write the implementation** — add to `leto/store.py`

```python
    def redirect_edges(self, from_slug: str, to_slug: str) -> None:
        parents = list(self._graph.parents(from_slug, label="relates_to"))  # beaver: parents
        for parent in parents:
            self._graph.unlink(parent, from_slug, label="relates_to")       # beaver: unlink
            self._graph.link(parent, to_slug, label="relates_to")           # beaver: link
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -q`
Expected: all store tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/store.py tests/test_store.py
git commit -m "feat(store): redirect_edges relinks incoming edges to canonical

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Consolidate — RRF `rerank` (pure function)

Reciprocal Rank Fusion over ranked id-lists. Pure, deterministic, no beaver dependency — this replaces the non-existent `beaver.rerank`.

**Files:**
- Create: `leto/consolidate.py`
- Test: `tests/test_consolidate.py`

**Interfaces:**
- Produces: `rerank(*rankings: list[str], k: int = 60) -> list[str]` — each argument is a list of ids in rank order; returns a single fused id-list, best first. An id in more/higher ranks scores higher; ties broken by first appearance order (Python dict insertion order → stable).

- [ ] **Step 1: Write the failing test** `tests/test_consolidate.py`

```python
from leto.consolidate import rerank


def test_rerank_ranks_item_present_in_both_lists_first():
    vector = ["a", "b", "c"]
    keyword = ["b", "d", "a"]
    fused = rerank(vector, keyword)
    # 'a' (ranks 0 and 2) and 'b' (ranks 1 and 0) beat singletons c, d
    assert set(fused[:2]) == {"a", "b"}
    assert "c" in fused and "d" in fused


def test_rerank_empty_inputs_return_empty():
    assert rerank([], []) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'leto.consolidate'`.

- [ ] **Step 3: Write minimal implementation** `leto/consolidate.py`

```python
from __future__ import annotations


def rerank(*rankings: list[str], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion over ranked id-lists (best first)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda i: scores[i], reverse=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add leto/consolidate.py tests/test_consolidate.py
git commit -m "feat(consolidate): RRF rerank pure function

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Consolidate — `Consolidator` + candidate blocking

The `Consolidator` holds the store + four injected sync callables. `_candidate_pairs` embeds each note, fuses vector ∪ FTS hits with RRF, excludes self, caps at 5, and returns unordered unique pairs.

**Files:**
- Modify: `leto/consolidate.py`
- Test: `tests/test_consolidate.py` (append) — establishes the shared fakes used by Tasks 8–12.

**Interfaces:**
- Consumes: `NoteStore` (`search_vector`, `match`, `all_notes`); `Note` (`leto.model`); `rerank`.
- Produces:
  - Type aliases: `Embedder = Callable[[str], list[float]]`, `Judge = Callable[[Note, Note], bool]`, `Merger = Callable[[list[Note]], MergedNote]`, `Gate = Callable[[Note, Settlement], bool]`.
  - `Consolidator(store, embedder, judge, merger, gate, *, candidate_cap: int = 5)`.
  - `Consolidator._candidate_pairs() -> set[tuple[str, str]]` (each tuple sorted; no self-pairs).

- [ ] **Step 1: Write the failing test** — append to `tests/test_consolidate.py`

```python
import re

import pytest

from leto.model import MergedNote, Note, NoteKind, Settlement
from leto.store import NoteStore
from leto.consolidate import Consolidator


# --- deterministic fakes (NO real LLM/embedder) -------------------------------

VOCAB = ["alan", "turing", "water", "computer", "science", "liquid", "oxygen"]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def fake_embedder(text: str) -> list[float]:
    toks = _tokens(text)
    return [1.0 if w in toks else 0.0 for w in VOCAB]


def title_stem_judge(a: Note, b: Note) -> bool:
    # same entity iff their titles share the same token set
    return _tokens(a.title) == _tokens(b.title)


def concat_merger(notes: list[Note]) -> MergedNote:
    ordered = sorted(notes, key=lambda n: n.slug)
    return MergedNote(title=ordered[0].title,
                      body="\n\n".join(n.body for n in ordered if n.body))


def approve_gate(note: Note, level: Settlement) -> bool:
    return True


def deny_gate(note: Note, level: Settlement) -> bool:
    return False


@pytest.fixture
def store(tmp_path):
    s = NoteStore(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield s
    s.close()


def _make(store, slug, title, body, sources=None):
    note = Note(slug=slug, kind=NoteKind.ENTITY, title=title, body=body,
                sources=sources or ["s0"])
    store.put(note, embedding=fake_embedder(f"{title}\n{body}"))
    return note


def test_blocking_finds_duplicate_pair_and_excludes_unrelated(store):
    _make(store, "alan-turing", "Alan Turing", "mathematician computer science")
    _make(store, "turing-alan", "Turing, Alan", "computer science pioneer")
    _make(store, "water", "Water", "liquid oxygen")
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)
    pairs = c._candidate_pairs()
    assert ("alan-turing", "turing-alan") in pairs
    assert not any("water" in p for p in pairs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: FAIL — `Consolidator` has no `_candidate_pairs` (or `ImportError` for `Consolidator`).

- [ ] **Step 3: Write the implementation** — edit `leto/consolidate.py`

Add imports + type aliases at the top (below the existing `from __future__` line):

```python
from typing import Callable

from leto.model import MergedNote, Note, Settlement
from leto.store import NoteStore

Embedder = Callable[[str], list[float]]
Judge = Callable[[Note, Note], bool]
Merger = Callable[[list[Note]], MergedNote]
Gate = Callable[[Note, Settlement], bool]
```

Append the class:

```python
class Consolidator:
    def __init__(
        self,
        store: NoteStore,
        embedder: Embedder,
        judge: Judge,
        merger: Merger,
        gate: Gate,
        *,
        candidate_cap: int = 5,
    ):
        self._store = store
        self._embed = embedder
        self._judge = judge
        self._merge = merger
        self._gate = gate
        self._cap = candidate_cap

    def _candidate_pairs(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for note in self._store.all_notes():
            text = f"{note.title}\n{note.body}"
            vector_hits = [
                n.slug for n, _ in self._store.search_vector(
                    self._embed(text), top_k=self._cap + 1)
            ]
            keyword_hits = [
                n.slug for n, _ in self._store.match(text, top_k=self._cap + 1)
            ]
            fused = rerank(vector_hits, keyword_hits)
            taken = 0
            for cand in fused:
                if cand == note.slug:
                    continue
                pairs.add(tuple(sorted((note.slug, cand))))
                taken += 1
                if taken >= self._cap:
                    break
        return pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: all consolidate tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/consolidate.py tests/test_consolidate.py
git commit -m "feat(consolidate): Consolidator + candidate blocking (RRF fusion)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Consolidate — judge + union-find clustering

Confirm candidate pairs with the injected `judge`; union confirmed pairs into clusters. Only clusters of size ≥ 2 survive.

**Files:**
- Modify: `leto/consolidate.py`
- Test: `tests/test_consolidate.py` (append)

**Interfaces:**
- Produces: `Consolidator._clusters() -> list[list[str]]` — lists of slugs, each `len >= 2`, built from judge-confirmed candidate pairs via union-find.

- [ ] **Step 1: Write the failing test** — append to `tests/test_consolidate.py`

```python
def test_clusters_groups_confirmed_duplicates(store):
    _make(store, "alan-turing", "Alan Turing", "mathematician computer science")
    _make(store, "turing-alan", "Turing, Alan", "Alan Turing pioneer")
    _make(store, "water", "Water", "liquid oxygen")
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)
    clusters = c._clusters()
    assert len(clusters) == 1
    assert set(clusters[0]) == {"alan-turing", "turing-alan"}
```

> The judge compares *title* token sets: `Alan Turing` vs `Turing, Alan` → both `{alan, turing}` → True; `Water` → `{water}` → never matches.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: FAIL with `AttributeError: 'Consolidator' object has no attribute '_clusters'`.

- [ ] **Step 3: Write the implementation** — add to `leto/consolidate.py`

```python
    def _clusters(self) -> list[list[str]]:
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            parent[find(a)] = find(b)

        confirmed: set[str] = set()
        for a, b in self._candidate_pairs():
            na, nb = self._store.get(a), self._store.get(b)
            if na is not None and nb is not None and self._judge(na, nb):
                union(a, b)
                confirmed.update((a, b))

        groups: dict[str, list[str]] = {}
        for slug in confirmed:
            groups.setdefault(find(slug), []).append(slug)
        return [sorted(g) for g in groups.values() if len(g) >= 2]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: all consolidate tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/consolidate.py tests/test_consolidate.py
git commit -m "feat(consolidate): judge-confirmed union-find clustering

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Consolidate — merge canonicalization

Fuse one cluster into a canonical note (spec §5): pick survivor slug, build the canonical note (merger's title+body, unioned links/sources, max settlement), redirect incoming edges, delete + alias absorbed notes, persist (re-embedded).

**Files:**
- Modify: `leto/consolidate.py`
- Test: `tests/test_consolidate.py` (append)

**Interfaces:**
- Consumes: `NoteStore.redirect_edges`, `delete`, `set_alias`, `put`, `get`; `MergedNote`, `MergeRecord`, `Settlement`.
- Produces:
  - Module-level `SETTLEMENT_ORDER = [Settlement.FLEETING, Settlement.DEVELOPING, Settlement.ESTABLISHED, Settlement.PERMANENT]`.
  - `Consolidator._merge_cluster(slugs: list[str]) -> MergeRecord`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_consolidate.py`

```python
def test_merge_cluster_produces_one_canonical_note(store):
    _make(store, "alan-turing", "Alan Turing", "Mathematician.", sources=["s1"])
    _make(store, "turing-alan", "Turing, Alan", "Codebreaker.", sources=["s2"])
    # something links to the soon-absorbed slug
    store.put(Note(slug="bletchley", kind=NoteKind.ENTITY, title="Bletchley",
                   body="Park.", links=["turing-alan"]),
              embedding=fake_embedder("Bletchley Park"))
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)

    rec = c._merge_cluster(["alan-turing", "turing-alan"])

    # survivor is lexicographically-first on the fleeting/1-source tie
    assert rec.canonical == "alan-turing"
    assert rec.absorbed == ["turing-alan"]
    # absorbed note is gone as a file but resolves via alias
    assert store.get("turing-alan").slug == "alan-turing"
    # provenance unioned onto the canonical
    canonical = store.get("alan-turing")
    assert set(canonical.sources) == {"s1", "s2"}
    assert "turing-alan" in canonical.aliases
    # incoming edge redirected: bletchley now points at the canonical
    assert [n.slug for n in store.neighbors("bletchley")] == ["alan-turing"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: FAIL with `AttributeError: 'Consolidator' object has no attribute '_merge_cluster'`.

- [ ] **Step 3: Write the implementation** — add to `leto/consolidate.py`

Add the module-level order list (below the type aliases):

```python
SETTLEMENT_ORDER = [
    Settlement.FLEETING,
    Settlement.DEVELOPING,
    Settlement.ESTABLISHED,
    Settlement.PERMANENT,
]
```

Add the imports for the record type (extend the existing `leto.model` import):

```python
from leto.model import MergedNote, MergeRecord, Note, Settlement
```

Add the method:

```python
    def _merge_cluster(self, slugs: list[str]) -> MergeRecord:
        notes = [n for n in (self._store.get(s) for s in slugs) if n is not None]
        survivor = sorted(
            notes,
            key=lambda n: (-SETTLEMENT_ORDER.index(n.settlement),
                           -len(set(n.sources)), n.slug),
        )[0]
        absorbed = [n for n in notes if n.slug != survivor.slug]
        absorbed_slugs = [n.slug for n in absorbed]

        merged = self._merge(notes)
        links = sorted(
            {link for n in notes for link in n.links}
            - {survivor.slug} - set(absorbed_slugs)
        )
        sources = sorted({s for n in notes for s in n.sources})
        settlement = max(notes, key=lambda n: SETTLEMENT_ORDER.index(n.settlement)).settlement
        aliases = sorted(
            set(survivor.aliases)
            | set(absorbed_slugs)
            | {a for n in absorbed for a in n.aliases}
        )

        canonical = Note(
            slug=survivor.slug,
            kind=survivor.kind,
            title=merged.title,
            body=merged.body,
            settlement=settlement,
            links=links,
            sources=sources,
            aliases=aliases,
        )

        for n in absorbed:
            self._store.redirect_edges(n.slug, survivor.slug)
            self._store.delete(n.slug)
            self._store.set_alias(n.slug, survivor.slug)

        self._store.put(
            canonical,
            embedding=self._embed(f"{canonical.title}\n{canonical.body}"),
        )
        return MergeRecord(
            canonical=survivor.slug,
            absorbed=absorbed_slugs,
            new_settlement=settlement.value,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: all consolidate tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/consolidate.py tests/test_consolidate.py
git commit -m "feat(consolidate): merge cluster into canonical note (§5)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Consolidate — settlement advancement

A surviving note advances one level iff distinct-source count ≥ threshold **and** the gate approves. Machine never sets `permanent`.

**Files:**
- Modify: `leto/consolidate.py`
- Test: `tests/test_consolidate.py` (append)

**Interfaces:**
- Produces:
  - Module-level `SETTLEMENT_THRESHOLD = {Settlement.DEVELOPING: 2, Settlement.ESTABLISHED: 3}`.
  - `Consolidator._advance(note: Note) -> str | None` — returns the new settlement value if advanced (and persists the note), else `None`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_consolidate.py`

```python
def test_advance_promotes_with_enough_sources_and_gate_true(store):
    note = _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1", "s2"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)
    assert c._advance(note) == "developing"
    assert store.get("alan-turing").settlement is Settlement.DEVELOPING


def test_advance_denied_by_gate_stays_put(store):
    note = _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1", "s2"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     deny_gate)
    assert c._advance(note) is None
    assert store.get("alan-turing").settlement is Settlement.FLEETING


def test_advance_denied_by_insufficient_sources(store):
    note = _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)
    assert c._advance(note) is None


def test_machine_never_sets_permanent(store):
    note = _make(store, "x", "X", "b",
                 sources=["s1", "s2", "s3", "s4"])
    note.settlement = Settlement.ESTABLISHED
    store.put(note, embedding=fake_embedder("X b"))
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)
    assert c._advance(store.get("x")) is None
    assert store.get("x").settlement is Settlement.ESTABLISHED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: FAIL with `AttributeError: 'Consolidator' object has no attribute '_advance'`.

- [ ] **Step 3: Write the implementation** — add to `leto/consolidate.py`

Add the threshold map (below `SETTLEMENT_ORDER`):

```python
SETTLEMENT_THRESHOLD = {
    Settlement.DEVELOPING: 2,
    Settlement.ESTABLISHED: 3,
}
```

Add the method:

```python
    def _advance(self, note: Note) -> str | None:
        idx = SETTLEMENT_ORDER.index(note.settlement)
        if idx + 1 >= len(SETTLEMENT_ORDER):
            return None
        nxt = SETTLEMENT_ORDER[idx + 1]
        if nxt not in SETTLEMENT_THRESHOLD:          # permanent is human-only
            return None
        if len(set(note.sources)) < SETTLEMENT_THRESHOLD[nxt]:
            return None
        if not self._gate(note, nxt):
            return None
        note.settlement = nxt
        self._store.put(
            note, embedding=self._embed(f"{note.title}\n{note.body}"))
        return nxt.value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: all consolidate tests pass.

- [ ] **Step 5: Commit**

```bash
git add leto/consolidate.py tests/test_consolidate.py
git commit -m "feat(consolidate): hybrid settlement advancement (count + gate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Consolidate — full `settle()` pipeline + idempotency

Wire blocking → cluster → merge → advance into `Consolidator.settle() -> SettleReport`. Prove idempotency: a second `settle()` with no new ingestion returns an empty report.

**Files:**
- Modify: `leto/consolidate.py`
- Test: `tests/test_consolidate.py` (append)

**Interfaces:**
- Consumes: `SettleReport` (`leto.model`), all `Consolidator` methods above.
- Produces: `Consolidator.settle() -> SettleReport`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_consolidate.py`

```python
from leto.model import SettleReport


def test_settle_merges_then_advances_then_is_idempotent(store):
    # two spellings of Turing from two distinct sources + an unrelated note
    _make(store, "alan-turing", "Alan Turing", "Mathematician.", sources=["s1"])
    _make(store, "turing-alan", "Turing, Alan", "Codebreaker.", sources=["s2"])
    _make(store, "water", "Water", "liquid oxygen", sources=["s1"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)

    report = c.settle()
    assert isinstance(report, SettleReport)
    assert [r.canonical for r in report.merged] == ["alan-turing"]
    # merged canonical now has 2 distinct sources + gate True -> promoted
    assert "alan-turing" in report.promoted
    assert store.get("alan-turing").settlement is Settlement.DEVELOPING

    # second pass: nothing new ingested -> no merges, no further promotion
    again = c.settle()
    assert again.merged == []
    assert again.promoted == []
```

> Idempotency holds because: the duplicate is already absorbed (only `alan-turing` + `water` remain, judge says they differ → no cluster), and `alan-turing` is now `developing` needing 3 sources for `established` but still having 2 → no advance.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: FAIL with `AttributeError: 'Consolidator' object has no attribute 'settle'`.

- [ ] **Step 3: Write the implementation** — add to `leto/consolidate.py`

Extend the `leto.model` import with `SettleReport`:

```python
from leto.model import MergedNote, MergeRecord, Note, Settlement, SettleReport
```

Add the method:

```python
    def settle(self) -> SettleReport:
        report = SettleReport()
        for cluster in self._clusters():
            report.merged.append(self._merge_cluster(cluster))
        for note in self._store.all_notes():
            if self._advance(note) is not None:
                report.promoted.append(note.slug)
        return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consolidate.py -q`
Expected: all consolidate tests pass.

- [ ] **Step 5: Run the full suite (VS1 engine tests will still fail — expected, fixed in Task 13)**

Run: `uv run pytest -q`
Expected: `test_consolidate.py`, model, markdown, store all green; `test_engine.py` / `test_vs1_end_to_end.py` still on the **old** `ingest` signature — untouched, still passing (they don't pass `source` yet because we haven't changed `ingest`). If they pass, good; Task 13 changes the signature and updates them together.

- [ ] **Step 6: Commit**

```bash
git add leto/consolidate.py tests/test_consolidate.py
git commit -m "feat(consolidate): settle() pipeline (block/cluster/merge/advance) + idempotency

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Engine — `ingest(text, source)` with embedding + provenance

Change `ingest` to take a `source`, embed each note, and record `sources=[source]`. This **breaks the VS1 signature**, so the VS1 engine + end-to-end tests are updated in the same task (per spec §4 and the handoff).

**Files:**
- Modify: `leto/engine.py`
- Test: `tests/test_engine.py` (update), `tests/test_vs1_end_to_end.py` (update)

**Interfaces:**
- Consumes: `NoteStore.put(note, embedding=...)`; `Embedder` type (`leto.consolidate`).
- Produces:
  - `Engine.__init__(self, store, extractor, embedder, judge=None, merger=None, gate=None, *, candidate_cap=5)`.
  - `Engine.ingest(text: str, source: str) -> list[Note]` — each note `settlement=FLEETING`, `sources=[source]`, embedding indexed.
  - `Engine.recall` unchanged.

- [ ] **Step 1: Update the engine tests** `tests/test_engine.py`

Add a deterministic fake embedder and thread `embedder=` + `source=` through the fixture and calls. Replace the top of the file (imports + fake + fixture) with:

```python
import re

import pytest

from leto.model import ExtractedItem, NoteKind, Settlement
from leto.store import NoteStore
from leto.engine import Engine


def fake_extractor(text: str):
    # deterministic — no LLM
    return [
        ExtractedItem(kind=NoteKind.ENTITY, title="Alan Turing",
                      body="A mathematician who founded computer science.",
                      links=["Computer Science"]),
        ExtractedItem(kind=NoteKind.ENTITY, title="Computer Science",
                      body="The study of computation and algorithms."),
        ExtractedItem(kind=NoteKind.PROCEDURE, title="Break a cipher",
                      body="Model the machine, then search the key space.",
                      links=["Alan Turing"]),
    ]


def fake_embedder(text: str) -> list[float]:
    vocab = ["alan", "turing", "computer", "science", "cipher", "machine", "key"]
    toks = set(re.findall(r"[a-z0-9]+", text.lower()))
    return [1.0 if w in toks else 0.0 for w in vocab]


@pytest.fixture
def engine(tmp_path):
    store = NoteStore(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield Engine(store=store, extractor=fake_extractor, embedder=fake_embedder)
    store.close()
```

Then update the three test bodies to pass a `source` and assert provenance. Replace each `engine.ingest("...")` / `engine.ingest("... any text ...")` call with a sourced call, and add a provenance assertion to the first test:

```python
def test_ingest_writes_fleeting_notes_with_slugged_links(engine):
    notes = engine.ingest("... any text ...", source="https://src/1")
    assert len(notes) == 3
    assert all(n.settlement is Settlement.FLEETING for n in notes)
    assert all(n.sources == ["https://src/1"] for n in notes)
    turing = next(n for n in notes if n.slug == "alan-turing")
    assert turing.kind is NoteKind.ENTITY
    assert turing.links == ["computer-science"]


def test_ingested_notes_are_retrievable_from_store(engine):
    engine.ingest("...", source="https://src/1")
    assert engine._store.get("break-a-cipher").kind is NoteKind.PROCEDURE


def test_recall_returns_settlement_tagged_blob_with_graph_expansion(engine):
    engine.ingest("...", source="https://src/1")
    blob = engine.recall("cipher key space", top_k=5)
    assert blob.query == "cipher key space"
    proc_slugs = [r.note.slug for r in blob.procedures]
    assert "break-a-cipher" in proc_slugs
    fact_slugs = [r.note.slug for r in blob.facts]
    assert "alan-turing" in fact_slugs
    turing = next(r for r in blob.facts if r.note.slug == "alan-turing")
    assert turing.via == "graph"
    assert all(r.note.settlement.value == "fleeting"
               for r in blob.facts + blob.procedures)
```

- [ ] **Step 2: Update the VS1 end-to-end test** `tests/test_vs1_end_to_end.py`

```python
import re

from leto import Engine, NoteStore
from leto.model import ExtractedItem, NoteKind


def extractor(text: str):
    return [
        ExtractedItem(kind=NoteKind.ENTITY, title="Alan Turing",
                      body="A mathematician who founded computer science."),
        ExtractedItem(kind=NoteKind.PROCEDURE, title="Break Enigma",
                      body="Model the rotors, then search the key space daily.",
                      links=["Alan Turing"]),
    ]


def embedder(text: str) -> list[float]:
    vocab = ["alan", "turing", "enigma", "rotors", "key", "space"]
    toks = set(re.findall(r"[a-z0-9]+", text.lower()))
    return [1.0 if w in toks else 0.0 for w in vocab]


def test_vs1_ingest_then_recall(tmp_path):
    store = NoteStore(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    engine = Engine(store=store, extractor=extractor, embedder=embedder)

    engine.ingest("Turing broke Enigma at Bletchley.", source="https://bletchley")
    assert (tmp_path / "notes" / "alan-turing.md").exists()
    assert (tmp_path / "notes" / "break-enigma.md").exists()

    blob = engine.recall("search the key space", top_k=5)
    assert "break-enigma" in [r.note.slug for r in blob.procedures]
    assert "alan-turing" in [r.note.slug for r in blob.facts]
    assert all(r.note.settlement.value == "fleeting"
               for r in blob.facts + blob.procedures)

    store.close()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_engine.py tests/test_vs1_end_to_end.py -q`
Expected: FAIL — `Engine.__init__` got an unexpected keyword `embedder` / `ingest` got unexpected keyword `source`.

- [ ] **Step 4: Update the implementation** `leto/engine.py`

Replace the imports and `Engine.__init__`/`ingest` (keep `recall` and `_add` unchanged):

```python
from __future__ import annotations

from typing import Callable

from leto.consolidate import Consolidator, Embedder, Gate, Judge, Merger
from leto.model import (
    ExtractedItem, KnowledgeBlob, Note, NoteKind, RecalledNote, Settlement,
    SettleReport, slugify,
)
from leto.store import NoteStore

Extractor = Callable[[str], list[ExtractedItem]]


class Engine:
    def __init__(
        self,
        store: NoteStore,
        extractor: Extractor,
        embedder: Embedder,
        judge: Judge | None = None,
        merger: Merger | None = None,
        gate: Gate | None = None,
        *,
        candidate_cap: int = 5,
    ):
        self._store = store
        self._extract = extractor
        self._embed = embedder
        self._consolidator: Consolidator | None = None
        if judge and merger and gate:
            self._consolidator = Consolidator(
                store, embedder, judge, merger, gate, candidate_cap=candidate_cap)

    def ingest(self, text: str, source: str) -> list[Note]:
        notes: list[Note] = []
        for item in self._extract(text):
            note = Note(
                slug=slugify(item.title),
                kind=item.kind,
                title=item.title,
                body=item.body,
                settlement=Settlement.FLEETING,
                links=[slugify(link) for link in item.links],
                sources=[source],
            )
            self._store.put(
                note, embedding=self._embed(f"{note.title}\n{note.body}"))
            notes.append(note)
        return notes
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_engine.py tests/test_vs1_end_to_end.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add leto/engine.py tests/test_engine.py tests/test_vs1_end_to_end.py
git commit -m "feat(engine): ingest(text, source) embeds + records provenance

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Engine — `settle()` delegation + consolidation acceptance test

`Engine.settle()` delegates to the injected `Consolidator`. A full acceptance test drives the slice end-to-end: ingest the same entity from two sources → `settle()` → one canonical note, alias resolves, provenance unioned, settlement advanced.

**Files:**
- Modify: `leto/engine.py`
- Test: `tests/test_consolidation_end_to_end.py` (create)

**Interfaces:**
- Produces: `Engine.settle() -> SettleReport` (raises `RuntimeError` if judge/merger/gate were not supplied).

- [ ] **Step 1: Write the failing acceptance test** `tests/test_consolidation_end_to_end.py`

```python
import re

import pytest

from leto import Engine, NoteStore
from leto.model import ExtractedItem, MergedNote, Note, NoteKind, Settlement


def embedder(text: str) -> list[float]:
    vocab = ["alan", "turing", "codebreaker", "mathematician", "water", "liquid"]
    toks = set(re.findall(r"[a-z0-9]+", text.lower()))
    return [1.0 if w in toks else 0.0 for w in vocab]


def title_stem_judge(a: Note, b: Note) -> bool:
    stem = lambda t: set(re.findall(r"[a-z0-9]+", t.lower()))
    return stem(a.title) == stem(b.title)


def concat_merger(notes: list[Note]) -> MergedNote:
    ordered = sorted(notes, key=lambda n: n.slug)
    return MergedNote(title=ordered[0].title,
                      body="\n\n".join(n.body for n in ordered if n.body))


def approve_gate(note: Note, level: Settlement) -> bool:
    return True


def _extractor_for(title: str, body: str):
    def extract(text: str):
        return [ExtractedItem(kind=NoteKind.ENTITY, title=title, body=body)]
    return extract


def test_settle_requires_consolidation_deps(tmp_path):
    store = NoteStore(folder=tmp_path / "n", db_path=tmp_path / "leto.db")
    engine = Engine(store=store, extractor=_extractor_for("X", "y"),
                    embedder=embedder)
    with pytest.raises(RuntimeError):
        engine.settle()
    store.close()


def test_two_sources_of_same_entity_merge_and_advance(tmp_path):
    store = NoteStore(folder=tmp_path / "n", db_path=tmp_path / "leto.db")

    # source 1: "Alan Turing" the mathematician
    Engine(store=store, extractor=_extractor_for("Alan Turing", "Mathematician."),
           embedder=embedder).ingest("...", source="https://s1")
    # source 2: "Turing, Alan" the codebreaker — same entity, different spelling
    engine = Engine(
        store=store,
        extractor=_extractor_for("Turing, Alan", "Codebreaker."),
        embedder=embedder,
        judge=title_stem_judge, merger=concat_merger, gate=approve_gate,
    )
    engine.ingest("...", source="https://s2")

    report = engine.settle()

    assert [r.canonical for r in report.merged] == ["alan-turing"]
    # alias resolves the absorbed spelling
    assert store.get("turing-alan").slug == "alan-turing"
    canonical = store.get("alan-turing")
    assert set(canonical.sources) == {"https://s1", "https://s2"}
    # 2 distinct sources + gate True -> advanced off fleeting
    assert canonical.settlement is Settlement.DEVELOPING
    assert "alan-turing" in report.promoted

    store.close()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_consolidation_end_to_end.py -q`
Expected: FAIL with `AttributeError: 'Engine' object has no attribute 'settle'`.

- [ ] **Step 3: Add `settle` to** `leto/engine.py`

Append to the `Engine` class (after `ingest`, before `recall`):

```python
    def settle(self) -> SettleReport:
        if self._consolidator is None:
            raise RuntimeError(
                "settle() requires judge, merger, and gate to be configured")
        return self._consolidator.settle()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_consolidation_end_to_end.py -q`
Expected: 2 passed.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: everything green (model, markdown, store, consolidate, engine, both end-to-end suites, smoke).

- [ ] **Step 6: Commit**

```bash
git add leto/engine.py tests/test_consolidation_end_to_end.py
git commit -m "feat(engine): settle() delegates to Consolidator + e2e acceptance

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: lingo-backed default backends + public API + optional extra

Provide the real (non-test) defaults for `Embedder`/`Judge`/`Merger`/`Gate`, each a single structured `lingo` pass bridged async→sync. **Not unit-tested** (non-deterministic) — smoke-tested manually. Export the new public API and add `lingo-ai` as an optional extra.

**Files:**
- Create: `leto/backends_lingo.py`
- Modify: `leto/__init__.py`, `pyproject.toml`

**Interfaces:**
- Consumes: `lingo.Engine`, `lingo.Context`, `lingo.Embedder`, `lingo.LLM` (async APIs, bridged with `asyncio.run`); `Note`, `MergedNote`, `Settlement` (`leto.model`).
- Produces (all sync, matching the injected callable types):
  - `lingo_embedder(**kwargs) -> Embedder`
  - `lingo_judge(engine) -> Judge`
  - `lingo_merger(engine) -> Merger`
  - `lingo_gate(engine) -> Gate`

- [ ] **Step 1: Add the optional extra to `pyproject.toml`**

Under `[project.optional-dependencies]`, add an `llm` extra (keep the existing `dev`):

```toml
[project.optional-dependencies]
dev = ["pytest"]
llm = ["lingo-ai>=2.1.0"]
```

- [ ] **Step 2: Write the backends module** `leto/backends_lingo.py`

> These are the production defaults, wired to real models. They are intentionally **not** unit-tested — the deterministic fakes in the test suite stand in for them. Verify by manual smoke (Step 4). `lingo.Engine.create` is async and takes a `Context`; each backend wraps one call in `asyncio.run`.

```python
"""Default LLM/embedding backends for consolidation, wired to lingo.

NOT unit-tested (non-deterministic). Install with:  uv sync --extra llm
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel

from leto.consolidate import Embedder, Gate, Judge, Merger
from leto.model import MergedNote, Note, Settlement


class _SameEntity(BaseModel):
    """Whether two notes describe the same real-world entity."""
    same: bool


class _Approve(BaseModel):
    """Whether the note is coherent and complete enough to advance a level."""
    approve: bool


def lingo_embedder(**kwargs) -> Embedder:
    from lingo import Embedder as LingoEmbedder

    embedder = LingoEmbedder(**kwargs)

    def embed(text: str) -> list[float]:
        return asyncio.run(embedder.embed(text))

    return embed


def lingo_judge(engine) -> Judge:
    from lingo import Context

    def judge(a: Note, b: Note) -> bool:
        prompt = (
            f"Note A — title: {a.title}\n{a.body}\n\n"
            f"Note B — title: {b.title}\n{b.body}\n\n"
            "Do A and B describe the SAME real-world entity?"
        )
        result = asyncio.run(engine.create(Context(), _SameEntity, prompt))
        return result.same

    return judge


def lingo_merger(engine) -> Merger:
    from lingo import Context

    def merge(notes: list[Note]) -> MergedNote:
        joined = "\n\n---\n\n".join(f"{n.title}\n{n.body}" for n in notes)
        prompt = (
            "Fuse these notes about the same entity into ONE canonical note. "
            "Return a single clear title and a merged body with no duplication:"
            f"\n\n{joined}"
        )
        return asyncio.run(engine.create(Context(), MergedNote, prompt))

    return merge


def lingo_gate(engine) -> Gate:
    from lingo import Context

    def gate(note: Note, level: Settlement) -> bool:
        prompt = (
            f"Note title: {note.title}\n{note.body}\n\n"
            f"It has {len(set(note.sources))} corroborating sources. "
            f"Is it coherent and complete enough to be marked '{level.value}'?"
        )
        result = asyncio.run(engine.create(Context(), _Approve, prompt))
        return result.approve

    return gate
```

- [ ] **Step 3: Export the new public API** — replace `leto/__init__.py`

```python
"""LETO — Learning Engine Through Ontologies (engine core)."""

from leto.consolidate import (
    Consolidator, Embedder, Gate, Judge, Merger, rerank,
)
from leto.engine import Engine, Extractor
from leto.model import (
    ExtractedItem, KnowledgeBlob, MergedNote, MergeRecord, Note, NoteKind,
    RecalledNote, Settlement, SettleReport, slugify,
)
from leto.store import NoteStore

__version__ = "0.0.1"

__all__ = [
    "Engine", "Extractor", "NoteStore", "Consolidator",
    "Embedder", "Judge", "Merger", "Gate", "rerank",
    "Note", "NoteKind", "Settlement", "ExtractedItem",
    "RecalledNote", "KnowledgeBlob", "MergedNote", "MergeRecord",
    "SettleReport", "slugify", "__version__",
]
```

- [ ] **Step 4: Verify — full suite green + backends import cleanly**

Run:
```bash
uv sync --extra dev
uv run pytest -q
```
Expected: all tests pass.

Then confirm the public API imports (backends are not imported by the core, so this must not error even without the `llm` extra):

```bash
uv run python -c "import leto; print(sorted(leto.__all__))"
```
Expected: prints the export list, no ImportError.

> Manual smoke (optional, requires `uv sync --extra llm` + API creds; NOT part of the automated suite): construct a `lingo.Engine`, build `lingo_judge(engine)` / `lingo_merger(engine)` / `lingo_gate(engine)` + `lingo_embedder(...)`, wire them into `Engine(..., judge=, merger=, gate=)`, ingest two real overlapping sources, and eyeball that `settle()` merges the duplicate.

- [ ] **Step 5: Commit**

```bash
git add leto/backends_lingo.py leto/__init__.py pyproject.toml
git commit -m "feat(backends): lingo-backed default embedder/judge/merger/gate + public API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 6: Push + release the lock**

```bash
git push origin main
bin/ws-lock gc   # release is pid-scoped; gc clears this session's locks
```

---

## Self-Review

**Spec coverage (against `docs/design/2026-07-03-leto-ii-consolidation.md`):**
- §1 substrate — `ingest(text, source)` → Task 13; `sources`/`aliases` fields → Task 2; embeddings in ingest (separate vector collection, *corrected*) → Tasks 4 + 13; alias dict + alias-following `get` → Task 5. ✓
- §2 pipeline — blocking (RRF, *corrected to local `rerank`*) → Tasks 7–8; judge + union-find → Task 9; merge → Task 10; advance → Task 11; `SettleReport` + idempotency → Task 12. ✓
- §3 interfaces — `Consolidator` in `consolidate.py`, four sync callables, fakes in tests, lingo defaults in `backends_lingo.py` (not unit-tested) → Tasks 8, 15. ✓
- §4 data model & API — `Note` additions, `MergedNote`, `SettleReport`, `MergeRecord`, `Engine.ingest`/`settle`, `NoteStore` additions (`search_vector`, alias `get`, `redirect_edges`, `delete`) → Tasks 2, 4, 5, 6, 13, 14. ✓
- §5 merge canonicalization — survivor tie-break, canonical build, redirect incoming, delete+alias, re-embed persist → Task 10. ✓
- §6 advancement — thresholds {developing:2, established:3}, hybrid rule, permanent human-only, one level/pass → Task 11. ✓
- §7 testing — all four unit scenarios (blocking, merge, advancement×3, idempotency) covered in Tasks 8–12; smoke is manual in Task 15. ✓
- §8 open questions — all resolved in "Reality corrections" + Global Constraints (rerank path → local RRF; vector search → `db.vectors.near`; lingo `create` shape → async-bridged; candidate cap → 5; self-exclusion → in `_candidate_pairs`). ✓
- §9 out of scope — contradictions, procedural consolidation, `refactor()`, incremental scoping, Hebbian layer: no task touches them. ✓

**Placeholder scan:** No TBD/TODO. Task 1 is a verification spike that records confirmed values (already confirmed during planning), not a discovery placeholder.

**Type consistency:** `Note` (with `sources`/`aliases`), `MergedNote`, `MergeRecord`, `SettleReport` defined once (Task 2), consumed unchanged. `Consolidator` ctor `(store, embedder, judge, merger, gate, *, candidate_cap)` is identical in Tasks 8–14 and in `Engine.__init__`. Callable types (`Embedder`, `Judge`, `Merger`, `Gate`) defined once in `consolidate.py` (Task 8), imported by `engine.py` (Task 13) and `backends_lingo.py` (Task 15). Store method names (`put(note, embedding=)`, `search_vector`, `all_notes`, `get`, `set_alias`, `delete`, `redirect_edges`, `neighbors`, `match`, `close`) are consistent across Tasks 4–6 and their consumers. `settle()` returns `SettleReport` in both `Consolidator` and `Engine`.

**Known RC risk:** every beaver call-site is inside `NoteStore` and marked `# beaver:`. Task 1's spike re-confirms the corrected forms (`vectors.near`, `graph.parents`/`unlink`, `dict.fetch`, `docs.drop`) before any code depends on them; if the RC bumps again, only those marked lines change.
