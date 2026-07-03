from __future__ import annotations

from typing import Callable

from leto.consolidate import Consolidator, Embedder, Gate, Judge, Merger
from leto.model import (
    ExtractedItem, KnowledgeBlob, Note, NoteKind, RecalledNote, Settlement,
    SettleReport, slugify,
)
from leto.store import NoteStore

Extractor = Callable[[str], list[ExtractedItem]]


class Engine:
    def __init__(
        self,
        store: NoteStore,
        extractor: Extractor,
        embedder: Embedder,
        judge: Judge | None = None,
        merger: Merger | None = None,
        gate: Gate | None = None,
        *,
        candidate_cap: int = 5,
    ):
        self._store = store
        self._extract = extractor
        self._embed = embedder
        self._consolidator: Consolidator | None = None
        if judge and merger and gate:
            self._consolidator = Consolidator(
                store, embedder, judge, merger, gate, candidate_cap=candidate_cap)

    def ingest(self, text: str, source: str) -> list[Note]:
        notes: list[Note] = []
        for item in self._extract(text):
            slug = slugify(item.title)
            links = [slugify(link) for link in item.links]
            existing = self._store.get(slug)
            if existing is not None:
                # Same entity re-encountered: accumulate provenance and links,
                # keep the existing body and settlement. This is how a note's
                # distinct-source count grows across cycles so it can climb the
                # settlement gradient — without waiting on a merge.
                existing.sources = sorted(set(existing.sources) | {source})
                existing.links = sorted(set(existing.links) | set(links))
                self._store.put(existing)
                notes.append(existing)
            else:
                note = Note(
                    slug=slug,
                    kind=item.kind,
                    title=item.title,
                    body=item.body,
                    settlement=Settlement.FLEETING,
                    links=links,
                    sources=[source],
                )
                self._store.put(
                    note, embedding=self._embed(f"{note.title}\n{note.body}"))
                notes.append(note)
        return notes

    def settle(self) -> SettleReport:
        if self._consolidator is None:
            raise RuntimeError(
                "settle() requires judge, merger, and gate to be configured")
        return self._consolidator.settle()

    def recall(self, query: str, top_k: int = 5) -> KnowledgeBlob:
        blob = KnowledgeBlob(query=query)
        seen: set[str] = set()
        for note, score in self._store.match(query, top_k=top_k):
            self._add(blob, RecalledNote(note=note, score=score, via="match"), seen)
            for neighbor in self._store.neighbors(note.slug):
                self._add(
                    blob,
                    RecalledNote(note=neighbor, score=0.0, via="graph"),
                    seen,
                )
        return blob

    @staticmethod
    def _add(blob: KnowledgeBlob, recalled: RecalledNote, seen: set[str]) -> None:
        if recalled.note.slug in seen:
            return
        seen.add(recalled.note.slug)
        if recalled.note.kind is NoteKind.ENTITY:
            blob.facts.append(recalled)
        else:
            blob.procedures.append(recalled)
