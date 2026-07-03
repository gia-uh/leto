from pathlib import Path

import pytest

from leto.model import Note, NoteKind
from leto.store import NoteStore


@pytest.fixture
def store(tmp_path):
    s = NoteStore(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield s
    s.close()


def test_put_writes_canonical_markdown_file(store, tmp_path):
    note = Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                body="Founded computer science.")
    store.put(note)
    path = tmp_path / "notes" / "alan-turing.md"
    assert path.exists()
    assert "title: Alan Turing" in path.read_text(encoding="utf-8")


def test_get_reads_note_back(store):
    note = Note(slug="water", kind=NoteKind.ENTITY, title="Water",
                body="H2O, a liquid.")
    store.put(note)
    assert store.get("water") == note
    assert store.get("missing") is None


def test_match_finds_by_body_text(store):
    store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                   body="A mathematician who founded computer science."))
    store.put(Note(slug="water", kind=NoteKind.ENTITY, title="Water",
                   body="A liquid made of hydrogen and oxygen."))
    hits = store.match("mathematician", top_k=5)
    slugs = [n.slug for n, _ in hits]
    assert "alan-turing" in slugs
    assert "water" not in slugs


def test_neighbors_follows_existing_links(store):
    store.put(Note(slug="computer-science", kind=NoteKind.ENTITY,
                   title="Computer Science", body="Study of computation."))
    store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                   body="Founder.", links=["computer-science"]))
    nb = store.neighbors("alan-turing")
    assert [n.slug for n in nb] == ["computer-science"]


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


def test_redirect_edges_relinks_incoming_to_canonical(store):
    # x -> turing-alan ; after redirect, x -> alan-turing, not turing-alan
    store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing"))
    store.put(Note(slug="turing-alan", kind=NoteKind.ENTITY, title="Turing, Alan"))
    store.put(Note(slug="x", kind=NoteKind.ENTITY, title="X",
                   links=["turing-alan"]))
    store.redirect_edges("turing-alan", "alan-turing")
    assert [n.slug for n in store.neighbors("x")] == ["alan-turing"]
