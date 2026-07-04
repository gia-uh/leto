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
