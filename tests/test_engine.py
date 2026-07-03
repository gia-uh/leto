import re

import pytest
import pytest_asyncio

from leto.model import ExtractedItem, NoteKind, Settlement
from leto.store import NoteStore
from leto.engine import Engine


async def fake_extractor(text: str):
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


async def fake_embedder(text: str) -> list[float]:
    vocab = ["alan", "turing", "computer", "science", "cipher", "machine", "key"]
    toks = set(re.findall(r"[a-z0-9]+", text.lower()))
    return [1.0 if w in toks else 0.0 for w in vocab]


@pytest_asyncio.fixture
async def engine(tmp_path):
    store = await NoteStore.open(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield Engine(store=store, extractor=fake_extractor, embedder=fake_embedder)
    await store.close()


async def test_ingest_writes_fleeting_notes_with_slugged_links(engine):
    notes = await engine.ingest("... any text ...", source="https://src/1")
    assert len(notes) == 3
    assert all(n.settlement is Settlement.FLEETING for n in notes)
    assert all(n.sources == ["https://src/1"] for n in notes)
    turing = next(n for n in notes if n.slug == "alan-turing")
    assert turing.kind is NoteKind.ENTITY
    assert turing.links == ["computer-science"]


async def test_ingested_notes_are_retrievable_from_store(engine):
    await engine.ingest("...", source="https://src/1")
    assert (await engine._store.get("break-a-cipher")).kind is NoteKind.PROCEDURE


async def test_recall_returns_settlement_tagged_blob_with_graph_expansion(engine):
    await engine.ingest("...", source="https://src/1")
    blob = await engine.recall("cipher key space", top_k=5)
    assert blob.query == "cipher key space"
    proc_slugs = [r.note.slug for r in blob.procedures]
    assert "break-a-cipher" in proc_slugs
    fact_slugs = [r.note.slug for r in blob.facts]
    assert "alan-turing" in fact_slugs
    turing = next(r for r in blob.facts if r.note.slug == "alan-turing")
    assert turing.via == "graph"
    assert all(r.note.settlement.value == "fleeting"
               for r in blob.facts + blob.procedures)


async def test_reingest_same_entity_unions_sources_and_preserves_settlement(engine):
    await engine.ingest("first", source="https://s1")
    # bump a note up the gradient, as consolidation would
    turing = await engine._store.get("alan-turing")
    turing.settlement = Settlement.DEVELOPING
    await engine._store.put(turing)
    # re-encounter the same entities from a new source
    await engine.ingest("second", source="https://s2")
    again = await engine._store.get("alan-turing")
    assert set(again.sources) == {"https://s1", "https://s2"}   # provenance accrues
    assert again.settlement is Settlement.DEVELOPING            # not demoted
    assert "computer-science" in again.links                    # links preserved
