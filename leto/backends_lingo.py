"""Default LLM/embedding backends for consolidation, wired to lingo.

NOT unit-tested (non-deterministic). Install with:  uv sync --extra llm
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel

from leto.consolidate import Embedder, Gate, Judge, Merger
from leto.model import MergedNote, Note, Settlement


class _SameEntity(BaseModel):
    """Whether two notes describe the same real-world entity."""
    same: bool


class _Approve(BaseModel):
    """Whether the note is coherent and complete enough to advance a level."""
    approve: bool


def lingo_embedder(**kwargs) -> Embedder:
    from lingo import Embedder as LingoEmbedder

    embedder = LingoEmbedder(**kwargs)

    def embed(text: str) -> list[float]:
        return asyncio.run(embedder.embed(text))

    return embed


def lingo_judge(engine) -> Judge:
    from lingo import Context

    def judge(a: Note, b: Note) -> bool:
        prompt = (
            f"Note A — title: {a.title}\n{a.body}\n\n"
            f"Note B — title: {b.title}\n{b.body}\n\n"
            "Do A and B describe the SAME real-world entity?"
        )
        result = asyncio.run(engine.create(Context([]), _SameEntity, prompt))
        return result.same

    return judge


def lingo_merger(engine) -> Merger:
    from lingo import Context

    def merge(notes: list[Note]) -> MergedNote:
        joined = "\n\n---\n\n".join(f"{n.title}\n{n.body}" for n in notes)
        prompt = (
            "Fuse these notes about the same entity into ONE canonical note. "
            "Return a single clear title and a merged body with no duplication:"
            f"\n\n{joined}"
        )
        return asyncio.run(engine.create(Context([]), MergedNote, prompt))

    return merge


def lingo_gate(engine) -> Gate:
    from lingo import Context

    def gate(note: Note, level: Settlement) -> bool:
        prompt = (
            f"Note title: {note.title}\n{note.body}\n\n"
            f"It has {len(set(note.sources))} corroborating sources. "
            f"Is it coherent and complete enough to be marked '{level.value}'?"
        )
        result = asyncio.run(engine.create(Context([]), _Approve, prompt))
        return result.approve

    return gate
