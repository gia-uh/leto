from __future__ import annotations

import re
from typing import Callable

from leto.model import MergedNote, Note, Settlement
from leto.store import NoteStore

Embedder = Callable[[str], list[float]]
Judge = Callable[[Note, Note], bool]
Merger = Callable[[list[Note]], MergedNote]
Gate = Callable[[Note, Settlement], bool]


def rerank(*rankings: list[str], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion over ranked id-lists (best first)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda i: scores[i], reverse=True)


class Consolidator:
    def __init__(
        self,
        store: NoteStore,
        embedder: Embedder,
        judge: Judge,
        merger: Merger,
        gate: Gate,
        *,
        candidate_cap: int = 5,
    ):
        self._store = store
        self._embed = embedder
        self._judge = judge
        self._merge = merger
        self._gate = gate
        self._cap = candidate_cap

    def _candidate_pairs(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for note in self._store.all_notes():
            text = f"{note.title}\n{note.body}"
            vector_hits = [
                n.slug for n, _ in self._store.search_vector(
                    self._embed(text), top_k=self._cap + 1)
            ]
            # Tokenize to bare words: the raw title/body carries punctuation
            # (commas, etc.) that FTS5 parses as query syntax and rejects.
            query = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
            keyword_hits = [
                n.slug for n, _ in self._store.match(query, top_k=self._cap + 1)
            ]
            fused = rerank(vector_hits, keyword_hits)
            taken = 0
            for cand in fused:
                if cand == note.slug:
                    continue
                pairs.add(tuple(sorted((note.slug, cand))))
                taken += 1
                if taken >= self._cap:
                    break
        return pairs
