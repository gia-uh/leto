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


from leto.model import EpistemicState


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
