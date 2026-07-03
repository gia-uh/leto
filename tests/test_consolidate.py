import re

import pytest
import pytest_asyncio

from leto.consolidate import rerank
from leto.model import (
    MergedGroup, MergeRecord, Note, NoteKind, Settlement, SettleReport,
)
from leto.store import NoteStore
from leto.consolidate import Consolidator


# --- rerank is pure/sync --------------------------------------------------

def test_rerank_ranks_item_present_in_both_lists_first():
    fused = rerank(["a", "b", "c"], ["b", "d", "a"])
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


async def stem_resolver(notes: list[Note]) -> list[MergedGroup]:
    """Group cluster members by title token-set; a group of 2+ is 'same
    entity'. Mirrors the strict same-vs-related judgment, one call per cluster."""
    groups: dict[frozenset, list[Note]] = {}
    for n in notes:
        groups.setdefault(frozenset(_tokens(n.title)), []).append(n)
    out = []
    for members in groups.values():
        if len(members) >= 2:
            ordered = sorted(members, key=lambda n: n.slug)
            out.append(MergedGroup(
                members=[n.slug for n in ordered],
                title=ordered[0].title,
                body="\n\n".join(n.body for n in ordered if n.body)))
    return out


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


def _consolidator(store):
    return Consolidator(store, fake_embedder, stem_resolver, approve_gate)


async def test_candidate_clusters_co_cluster_the_duplicate_pair(store):
    await _make(store, "alan-turing", "Alan Turing", "mathematician computer science")
    await _make(store, "turing-alan", "Turing, Alan", "computer science pioneer")
    await _make(store, "water", "Water", "liquid oxygen")
    clusters = await _consolidator(store)._candidate_clusters()
    # cheap blocking (no LLM) puts the obvious duplicates in one component;
    # the resolver later splits out unrelated members.
    assert any({"alan-turing", "turing-alan"} <= set(c) for c in clusters)


async def test_commit_merge_produces_one_canonical_note(store):
    await _make(store, "alan-turing", "Alan Turing", "Mathematician.", sources=["s1"])
    await _make(store, "turing-alan", "Turing, Alan", "Codebreaker.", sources=["s2"])
    await store.put(Note(slug="bletchley", kind=NoteKind.ENTITY, title="Bletchley",
                         body="Park.", links=["turing-alan"]),
                    embedding=await fake_embedder("Bletchley Park"))
    group = MergedGroup(members=["alan-turing", "turing-alan"],
                        title="Alan Turing", body="Mathematician and codebreaker.")

    rec = await _consolidator(store)._commit_merge(group)

    assert rec.canonical == "alan-turing"
    assert rec.absorbed == ["turing-alan"]
    assert (await store.get("turing-alan")).slug == "alan-turing"
    canonical = await store.get("alan-turing")
    assert set(canonical.sources) == {"s1", "s2"}
    assert "turing-alan" in canonical.aliases
    assert canonical.body == "Mathematician and codebreaker."
    assert [n.slug for n in await store.neighbors("bletchley")] == ["alan-turing"]


async def test_advance_promotes_with_enough_sources_and_gate_true(store):
    note = await _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1", "s2"])
    assert await _consolidator(store)._advance(note) == "developing"
    assert (await store.get("alan-turing")).settlement is Settlement.DEVELOPING


async def test_advance_denied_by_gate_stays_put(store):
    note = await _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1", "s2"])
    c = Consolidator(store, fake_embedder, stem_resolver, deny_gate)
    assert await c._advance(note) is None
    assert (await store.get("alan-turing")).settlement is Settlement.FLEETING


async def test_advance_denied_by_insufficient_sources(store):
    note = await _make(store, "alan-turing", "Alan Turing", "M.", sources=["s1"])
    assert await _consolidator(store)._advance(note) is None


async def test_machine_never_sets_permanent(store):
    note = await _make(store, "x", "X", "b", sources=["s1", "s2", "s3", "s4"])
    note.settlement = Settlement.ESTABLISHED
    await store.put(note, embedding=await fake_embedder("X b"))
    assert await _consolidator(store)._advance(await store.get("x")) is None
    assert (await store.get("x")).settlement is Settlement.ESTABLISHED


async def test_settle_merges_resolver_groups_leaves_others_and_is_idempotent(store):
    await _make(store, "alan-turing", "Alan Turing", "Mathematician.", sources=["s1"])
    await _make(store, "turing-alan", "Turing, Alan", "Codebreaker.", sources=["s2"])
    await _make(store, "water", "Water", "liquid oxygen", sources=["s1"])
    c = _consolidator(store)

    report = await c.settle()
    assert isinstance(report, SettleReport)
    assert [r.canonical for r in report.merged] == ["alan-turing"]   # only the pair
    assert await store.get("water") is not None                      # unrelated kept
    assert "alan-turing" in report.promoted
    assert (await store.get("alan-turing")).settlement is Settlement.DEVELOPING

    again = await c.settle()
    assert again.merged == []
    assert again.promoted == []
