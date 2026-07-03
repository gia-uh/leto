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
