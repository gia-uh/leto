from __future__ import annotations


def rerank(*rankings: list[str], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion over ranked id-lists (best first)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda i: scores[i], reverse=True)
