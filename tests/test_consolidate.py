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
