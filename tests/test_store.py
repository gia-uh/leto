from pathlib import Path

import pytest
import pytest_asyncio

from leto.model import Note, NoteKind
from leto.store import NoteStore


@pytest_asyncio.fixture
async def store(tmp_path):
    s = await NoteStore.open(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield s
    await s.close()


async def test_put_writes_canonical_markdown_file(store, tmp_path):
    note = Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                body="Founded computer science.")
    await store.put(note)
    path = tmp_path / "notes" / "alan-turing.md"
    assert path.exists()
    assert "title: Alan Turing" in path.read_text(encoding="utf-8")


async def test_get_reads_note_back(store):
    note = Note(slug="water", kind=NoteKind.ENTITY, title="Water",
                body="H2O, a liquid.")
    await store.put(note)
    assert await store.get("water") == note
    assert await store.get("missing") is None


async def test_match_finds_by_body_text(store):
    await store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                         body="A mathematician who founded computer science."))
    await store.put(Note(slug="water", kind=NoteKind.ENTITY, title="Water",
                         body="A liquid made of hydrogen and oxygen."))
    hits = await store.match("mathematician", top_k=5)
    slugs = [n.slug for n, _ in hits]
    assert "alan-turing" in slugs
    assert "water" not in slugs


async def test_neighbors_follows_existing_links(store):
    await store.put(Note(slug="computer-science", kind=NoteKind.ENTITY,
                         title="Computer Science", body="Study of computation."))
    await store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                         body="Founder.", links=["computer-science"]))
    nb = await store.neighbors("alan-turing")
    assert [n.slug for n in nb] == ["computer-science"]


async def test_search_vector_ranks_by_nearness(store):
    await store.put(Note(slug="a", kind=NoteKind.ENTITY, title="A", body="x"),
                    embedding=[1.0, 0.0, 0.0])
    await store.put(Note(slug="b", kind=NoteKind.ENTITY, title="B", body="y"),
                    embedding=[0.0, 1.0, 0.0])
    hits = await store.search_vector([0.9, 0.1, 0.0], top_k=2)
    assert hits[0][0].slug == "a"


async def test_all_notes_enumerates_sorted(store):
    await store.put(Note(slug="water", kind=NoteKind.ENTITY, title="Water"))
    await store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing"))
    assert [n.slug for n in await store.all_notes()] == ["alan-turing", "water"]


async def test_delete_removes_file_and_get_returns_none(store, tmp_path):
    await store.put(Note(slug="water", kind=NoteKind.ENTITY, title="Water", body="H2O"),
                    embedding=[1.0, 0.0])
    await store.delete("water")
    assert not (tmp_path / "notes" / "water.md").exists()
    assert await store.get("water") is None


async def test_get_follows_alias_to_canonical(store):
    await store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
                         body="Founder."))
    await store.set_alias("turing-alan", "alan-turing")
    resolved = await store.get("turing-alan")
    assert resolved is not None
    assert resolved.slug == "alan-turing"


async def test_redirect_edges_relinks_incoming_to_canonical(store):
    # x -> turing-alan ; after redirect, x -> alan-turing, not turing-alan
    await store.put(Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing"))
    await store.put(Note(slug="turing-alan", kind=NoteKind.ENTITY, title="Turing, Alan"))
    await store.put(Note(slug="x", kind=NoteKind.ENTITY, title="X",
                         links=["turing-alan"]))
    await store.redirect_edges("turing-alan", "alan-turing")
    assert [n.slug for n in await store.neighbors("x")] == ["alan-turing"]
