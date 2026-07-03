from __future__ import annotations

from typing import Callable

from leto.model import (
    ExtractedItem, KnowledgeBlob, Note, NoteKind, RecalledNote, Settlement, slugify,
)
from leto.store import NoteStore

Extractor = Callable[[str], list[ExtractedItem]]


class Engine:
    def __init__(self, store: NoteStore, extractor: Extractor):
        self._store = store
        self._extract = extractor

    def ingest(self, text: str) -> list[Note]:
        notes: list[Note] = []
        for item in self._extract(text):
            note = Note(
                slug=slugify(item.title),
                kind=item.kind,
                title=item.title,
                body=item.body,
                settlement=Settlement.FLEETING,
                links=[slugify(link) for link in item.links],
            )
            self._store.put(note)
            notes.append(note)
        return notes
