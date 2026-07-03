from __future__ import annotations

import re
from typing import Awaitable, Callable

from leto.model import MergedNote, MergeRecord, Note, Settlement, SettleReport
from leto.store import NoteStore

Embedder = Callable[[str], Awaitable[list[float]]]
Judge = Callable[[Note, Note], Awaitable[bool]]
Merger = Callable[[list[Note]], Awaitable[MergedNote]]
Gate = Callable[[Note, Settlement], Awaitable[bool]]

SETTLEMENT_ORDER = [
    Settlement.FLEETING,
    Settlement.DEVELOPING,
    Settlement.ESTABLISHED,
    Settlement.PERMANENT,
]

SETTLEMENT_THRESHOLD = {
    Settlement.DEVELOPING: 2,
    Settlement.ESTABLISHED: 3,
}


def rerank(*rankings: list[str], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion over ranked id-lists (best first). Pure/sync."""
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

    async def _candidate_pairs(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for note in await self._store.all_notes():
            text = f"{note.title}\n{note.body}"
            vector_hits = [
                n.slug for n, _ in await self._store.search_vector(
                    await self._embed(text), top_k=self._cap + 1)
            ]
            # Tokenize to bare words: raw title/body carries punctuation that
            # FTS5 parses as query syntax and rejects.
            query = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
            keyword_hits = [
                n.slug for n, _ in await self._store.match(query, top_k=self._cap + 1)
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

    async def _clusters(self) -> list[list[str]]:
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            parent[find(a)] = find(b)

        confirmed: set[str] = set()
        for a, b in await self._candidate_pairs():
            na, nb = await self._store.get(a), await self._store.get(b)
            if na is not None and nb is not None and await self._judge(na, nb):
                union(a, b)
                confirmed.update((a, b))

        groups: dict[str, list[str]] = {}
        for slug in confirmed:
            groups.setdefault(find(slug), []).append(slug)
        return [sorted(g) for g in groups.values() if len(g) >= 2]

    async def _merge_cluster(self, slugs: list[str]) -> MergeRecord:
        notes = [n for n in [await self._store.get(s) for s in slugs] if n is not None]
        survivor = sorted(
            notes,
            key=lambda n: (-SETTLEMENT_ORDER.index(n.settlement),
                           -len(set(n.sources)), n.slug),
        )[0]
        absorbed = [n for n in notes if n.slug != survivor.slug]
        absorbed_slugs = [n.slug for n in absorbed]

        merged = await self._merge(notes)
        links = sorted(
            {link for n in notes for link in n.links}
            - {survivor.slug} - set(absorbed_slugs)
        )
        sources = sorted({s for n in notes for s in n.sources})
        settlement = max(
            notes, key=lambda n: SETTLEMENT_ORDER.index(n.settlement)).settlement
        aliases = sorted(
            set(survivor.aliases)
            | set(absorbed_slugs)
            | {a for n in absorbed for a in n.aliases}
        )

        canonical = Note(
            slug=survivor.slug,
            kind=survivor.kind,
            title=merged.title,
            body=merged.body,
            settlement=settlement,
            links=links,
            sources=sources,
            aliases=aliases,
        )

        for n in absorbed:
            await self._store.redirect_edges(n.slug, survivor.slug)
            await self._store.delete(n.slug)
            await self._store.set_alias(n.slug, survivor.slug)

        await self._store.put(
            canonical,
            embedding=await self._embed(f"{canonical.title}\n{canonical.body}"),
        )
        return MergeRecord(
            canonical=survivor.slug,
            absorbed=absorbed_slugs,
            new_settlement=settlement.value,
        )

    async def _advance(self, note: Note) -> str | None:
        idx = SETTLEMENT_ORDER.index(note.settlement)
        if idx + 1 >= len(SETTLEMENT_ORDER):
            return None
        nxt = SETTLEMENT_ORDER[idx + 1]
        if nxt not in SETTLEMENT_THRESHOLD:          # permanent is human-only
            return None
        if len(set(note.sources)) < SETTLEMENT_THRESHOLD[nxt]:
            return None
        if not await self._gate(note, nxt):
            return None
        note.settlement = nxt
        await self._store.put(
            note, embedding=await self._embed(f"{note.title}\n{note.body}"))
        return nxt.value

    async def settle(self) -> SettleReport:
        report = SettleReport()
        for cluster in await self._clusters():
            report.merged.append(await self._merge_cluster(cluster))
        for note in await self._store.all_notes():
            if await self._advance(note) is not None:
                report.promoted.append(note.slug)
        return report
