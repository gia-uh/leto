import re

import pytest

from leto import Engine, NoteStore
from leto.model import ExtractedItem, MergedNote, Note, NoteKind, Settlement


async def embedder(text: str) -> list[float]:
    vocab = ["alan", "turing", "codebreaker", "mathematician", "water", "liquid"]
    toks = set(re.findall(r"[a-z0-9]+", text.lower()))
    return [1.0 if w in toks else 0.0 for w in vocab]


async def title_stem_judge(a: Note, b: Note) -> bool:
    stem = lambda t: set(re.findall(r"[a-z0-9]+", t.lower()))
    return stem(a.title) == stem(b.title)


async def concat_merger(notes: list[Note]) -> MergedNote:
    ordered = sorted(notes, key=lambda n: n.slug)
    return MergedNote(title=ordered[0].title,
                      body="\n\n".join(n.body for n in ordered if n.body))


async def approve_gate(note: Note, level: Settlement) -> bool:
    return True


def _extractor_for(title: str, body: str):
    async def extract(text: str):
        return [ExtractedItem(kind=NoteKind.ENTITY, title=title, body=body)]
    return extract


async def test_settle_requires_consolidation_deps(tmp_path):
    store = await NoteStore.open(folder=tmp_path / "n", db_path=tmp_path / "leto.db")
    engine = Engine(store=store, extractor=_extractor_for("X", "y"), embedder=embedder)
    with pytest.raises(RuntimeError):
        await engine.settle()
    await store.close()


async def test_two_sources_of_same_entity_merge_and_advance(tmp_path):
    store = await NoteStore.open(folder=tmp_path / "n", db_path=tmp_path / "leto.db")

    # source 1: "Alan Turing" the mathematician
    await Engine(store=store, extractor=_extractor_for("Alan Turing", "Mathematician."),
                 embedder=embedder).ingest("...", source="https://s1")
    # source 2: "Turing, Alan" the codebreaker — same entity, different spelling
    engine = Engine(
        store=store,
        extractor=_extractor_for("Turing, Alan", "Codebreaker."),
        embedder=embedder,
        judge=title_stem_judge, merger=concat_merger, gate=approve_gate,
    )
    await engine.ingest("...", source="https://s2")

    report = await engine.settle()

    assert [r.canonical for r in report.merged] == ["alan-turing"]
    assert (await store.get("turing-alan")).slug == "alan-turing"
    canonical = await store.get("alan-turing")
    assert set(canonical.sources) == {"https://s1", "https://s2"}
    assert canonical.settlement is Settlement.DEVELOPING
    assert "alan-turing" in report.promoted

    await store.close()
