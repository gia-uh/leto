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


@pytest.fixture
def engine(tmp_path):
    store = NoteStore(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield Engine(store=store, extractor=fake_extractor)
    store.close()


def test_ingest_writes_fleeting_notes_with_slugged_links(engine):
    notes = engine.ingest("... any text ...")
    assert len(notes) == 3
    assert all(n.settlement is Settlement.FLEETING for n in notes)
    turing = next(n for n in notes if n.slug == "alan-turing")
    assert turing.kind is NoteKind.ENTITY
    assert turing.links == ["computer-science"]


def test_ingested_notes_are_retrievable_from_store(engine):
    engine.ingest("...")
    assert engine._store.get("break-a-cipher").kind is NoteKind.PROCEDURE


def test_recall_returns_settlement_tagged_blob_with_graph_expansion(engine):
    engine.ingest("...")
    # link procedure -> entity exists (Alan Turing written before Break a cipher)
    blob = engine.recall("cipher key space", top_k=5)
    assert blob.query == "cipher key space"
    proc_slugs = [r.note.slug for r in blob.procedures]
    assert "break-a-cipher" in proc_slugs
    # one-hop expansion pulled in the linked entity as a fact via graph
    fact_slugs = [r.note.slug for r in blob.facts]
    assert "alan-turing" in fact_slugs
    turing = next(r for r in blob.facts if r.note.slug == "alan-turing")
    assert turing.via == "graph"
    # settlement travels in the answer
    assert all(r.note.settlement.value == "fleeting"
               for r in blob.facts + blob.procedures)
