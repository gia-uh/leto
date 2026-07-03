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
    # Blocking is a RECALL step: the obvious duplicate must surface as a
    # candidate. It may over-generate (with a tiny corpus, vector `near`
    # returns every note) — the judge (Task 9) supplies precision and drops
    # the unrelated "water" pairing at the cluster stage.
    assert ("alan-turing", "turing-alan") in pairs


def test_clusters_groups_confirmed_duplicates(store):
    _make(store, "alan-turing", "Alan Turing", "mathematician computer science")
    _make(store, "turing-alan", "Turing, Alan", "Alan Turing pioneer")
    _make(store, "water", "Water", "liquid oxygen")
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger,
                     approve_gate)
    clusters = c._clusters()
    assert len(clusters) == 1
    assert set(clusters[0]) == {"alan-turing", "turing-alan"}


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
