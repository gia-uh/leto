import re

import pytest
import pytest_asyncio

from leto.consolidate import rerank
from leto.model import (
    MergedNote, MergeRecord, Note, NoteKind, Settlement, SettleReport,
)
from leto.store import NoteStore
from leto.consolidate import Consolidator


# --- rerank is pure/sync --------------------------------------------------

def test_rerank_ranks_item_present_in_both_lists_first():
    vector = ["a", "b", "c"]
    keyword = ["b", "d", "a"]
    fused = rerank(vector, keyword)
    assert set(fused[:2]) == {"a", "b"}
    assert "c" in fused and "d" in fused


def test_rerank_empty_inputs_return_empty():
    assert rerank([], []) == []


# --- deterministic ASYNC fakes (NO real LLM/embedder) ---------------------

VOCAB = ["alan", "turing", "water", "computer", "science", "liquid", "oxygen"]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


async def fake_embedder(text: str) -> list[float]:
    toks = _tokens(text)
    return [1.0 if w in toks else 0.0 for w in VOCAB]


async def title_stem_judge(a: Note, b: Note) -> bool:
    return _tokens(a.title) == _tokens(b.title)


async def concat_merger(notes: list[Note]) -> MergedNote:
    ordered = sorted(notes, key=lambda n: n.slug)
    return MergedNote(title=ordered[0].title,
                      body="\n\n".join(n.body for n in ordered if n.body))


async def approve_gate(note: Note, level: Settlement) -> bool:
    return True


async def deny_gate(note: Note, level: Settlement) -> bool:
    return False


@pytest_asyncio.fixture
async def store(tmp_path):
    s = await NoteStore.open(folder=tmp_path / "notes", db_path=tmp_path / "leto.db")
    yield s
    await s.close()


async def _make(store, slug, title, body, sources=None):
    note = Note(slug=slug, kind=NoteKind.ENTITY, title=title, body=body,
                sources=sources or ["s0"])
    await store.put(note, embedding=await fake_embedder(f"{title}\n{body}"))
    return note


async def test_blocking_finds_duplicate_pair_and_excludes_unrelated(store):
    await _make(store, "alan-turing", "Alan Turing", "mathematician computer science")
    await _make(store, "turing-alan", "Turing, Alan", "computer science pioneer")
    await _make(store, "water", "Water", "liquid oxygen")
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, approve_gate)
    pairs = await c._candidate_pairs()
    # Blocking is a RECALL step: the obvious duplicate must surface; it may
    # over-generate (tiny corpus). The judge (below) supplies precision.
    assert ("alan-turing", "turing-alan") in pairs


async def test_clusters_groups_confirmed_duplicates(store):
    await _make(store, "alan-turing", "Alan Turing", "mathematician computer science")
    await _make(store, "turing-alan", "Turing, Alan", "Alan Turing pioneer")
    await _make(store, "water", "Water", "liquid oxygen")
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, approve_gate)
    clusters = await c._clusters()
    assert len(clusters) == 1
    assert set(clusters[0]) == {"alan-turing", "turing-alan"}


async def test_merge_cluster_produces_one_canonical_note(store):
    await _make(store, "alan-turing", "Alan Turing", "Mathematician.", sources=["s1"])
    await _make(store, "turing-alan", "Turing, Alan", "Codebreaker.", sources=["s2"])
    await store.put(Note(slug="bletchley", kind=NoteKind.ENTITY, title="Bletchley",
                         body="Park.", links=["turing-alan"]),
                    embedding=await fake_embedder("Bletchley Park"))
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, approve_gate)

    rec = await c._merge_cluster(["alan-turing", "turing-alan"])

    assert rec.canonical == "alan-turing"
    assert rec.absorbed == ["turing-alan"]
    assert (await store.get("turing-alan")).slug == "alan-turing"
    canonical = await store.get("alan-turing")
    assert set(canonical.sources) == {"s1", "s2"}
    assert "turing-alan" in canonical.aliases
    assert [n.slug for n in await store.neighbors("bletchley")] == ["alan-turing"]


async def test_advance_promotes_with_enough_sources_and_gate_true(store):
    note = await _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1", "s2"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, approve_gate)
    assert await c._advance(note) == "developing"
    assert (await store.get("alan-turing")).settlement is Settlement.DEVELOPING


async def test_advance_denied_by_gate_stays_put(store):
    note = await _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1", "s2"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, deny_gate)
    assert await c._advance(note) is None
    assert (await store.get("alan-turing")).settlement is Settlement.FLEETING


async def test_advance_denied_by_insufficient_sources(store):
    note = await _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, approve_gate)
    assert await c._advance(note) is None


async def test_machine_never_sets_permanent(store):
    note = await _make(store, "x", "X", "b", sources=["s1", "s2", "s3", "s4"])
    note.settlement = Settlement.ESTABLISHED
    await store.put(note, embedding=await fake_embedder("X b"))
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, approve_gate)
    assert await c._advance(await store.get("x")) is None
    assert (await store.get("x")).settlement is Settlement.ESTABLISHED


async def test_settle_merges_then_advances_then_is_idempotent(store):
    await _make(store, "alan-turing", "Alan Turing", "Mathematician.", sources=["s1"])
    await _make(store, "turing-alan", "Turing, Alan", "Codebreaker.", sources=["s2"])
    await _make(store, "water", "Water", "liquid oxygen", sources=["s1"])
    c = Consolidator(store, fake_embedder, title_stem_judge, concat_merger, approve_gate)

    report = await c.settle()
    assert isinstance(report, SettleReport)
    assert [r.canonical for r in report.merged] == ["alan-turing"]
    assert "alan-turing" in report.promoted
    assert (await store.get("alan-turing")).settlement is Settlement.DEVELOPING

    again = await c.settle()
    assert again.merged == []
    assert again.promoted == []
