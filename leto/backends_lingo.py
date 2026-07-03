"""Default LLM/embedding backends for consolidation, wired to lingo (async).

NOT unit-tested (non-deterministic). Install with:  uv sync --extra llm

LETO is async-native, so these backends are plain async callables that `await`
lingo directly — no event-loop bridging.
"""
from __future__ import annotations

from pydantic import BaseModel

from leto.consolidate import Embedder, Gate, Merger
from leto.model import MergedGroup, Note, Settlement


class _Resolution(BaseModel):
    """The resolver's verdict on a candidate cluster: zero or more confirmed
    same-entity groups."""
    groups: list[MergedGroup]


class _Approve(BaseModel):
    """Whether the note is coherent and complete enough to advance a level."""
    approve: bool


def lingo_embedder(**kwargs) -> Embedder:
    from lingo import Embedder as LingoEmbedder

    embedder = LingoEmbedder(**kwargs)

    async def embed(text: str) -> list[float]:
        return await embedder.embed(text)

    return embed


def lingo_merger(engine) -> Merger:
    """A cluster resolver: given a candidate cluster (which may mix truly-same
    entities with merely-related ones), return one MergedGroup per confirmed
    same-entity group. ONE LLM call per cluster."""
    from lingo import Context

    async def merge(notes: list[Note]) -> list[MergedGroup]:
        listing = "\n".join(f"- [{n.slug}] {n.title}: {n.body}" for n in notes)
        prompt = (
            "Below is a candidate cluster of knowledge notes (each with a "
            "[slug]). They were grouped only by surface similarity, so some may "
            "be the SAME real-world entity and others merely related.\n\n"
            "Group ONLY the notes that are the same specific entity (same person, "
            "place, organization, device, method, or concept — possibly under "
            "different names/spellings). Do NOT group merely related things: a "
            "person vs. a thing they made; a place vs. someone who worked there; "
            "a method vs. its inventor; a whole vs. its parts.\n\n"
            "For each same-entity group of 2+ notes, return its member slugs and "
            "a fused canonical title + body (no duplication). Omit singletons.\n\n"
            f"{listing}"
        )
        return (await engine.create(Context([]), _Resolution, prompt)).groups

    return merge


def lingo_gate(engine) -> Gate:
    from lingo import Context

    async def gate(note: Note, level: Settlement) -> bool:
        prompt = (
            f"Note title: {note.title}\n{note.body}\n\n"
            f"It has {len(set(note.sources))} corroborating sources. "
            f"Is it coherent and complete enough to be marked '{level.value}'?"
        )
        result = await engine.create(Context([]), _Approve, prompt)
        return result.approve

    return gate
