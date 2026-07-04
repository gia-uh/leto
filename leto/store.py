from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from beaver import AsyncBeaverDB, Document
from pydantic import BaseModel

from leto.markdown import note_from_markdown, note_to_markdown
from leto.model import (
    Edge, EdgeType, Note, ORDERED_EDGES, edge_allowed, retrieval_key,
)


def NOW() -> str:
    """ISO-8601 UTC timestamp. Overridable in tests via monkeypatch."""
    return datetime.now(timezone.utc).isoformat()


class NoteDoc(BaseModel):
    slug: str
    key: str          # the retrieval key (FTS target)
    kind: str


class NoteStore:
    def __init__(self, folder: str | Path, db_path: str | Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self._db: AsyncBeaverDB | None = None

    @classmethod
    async def open(cls, folder: str | Path, db_path: str | Path) -> "NoteStore":
        self = cls(folder, db_path)
        self._db = AsyncBeaverDB(self._db_path)
        await self._db.connect()
        self._docs = self._db.docs("notes", model=NoteDoc)
        self._vectors = self._db.vectors("embeddings")
        self._graph = self._db.graph("edges")
        self._aliases = self._db.dict("aliases")
        return self

    async def put(self, note: Note, embedding: list[float] | None = None) -> Note:
        if note.recorded_at is None:
            note.recorded_at = NOW()
        if note.valid_from is None:
            note.valid_from = note.recorded_at
        (self.folder / f"{note.slug}.md").write_text(
            note_to_markdown(note), encoding="utf-8")
        await self._docs.index(document=Document(
            id=note.slug,
            body=NoteDoc(slug=note.slug, key=retrieval_key(note),
                         kind=note.kind.value)))
        if embedding is not None:
            await self._vectors.set(note.slug, embedding)
        return note

    async def get(self, slug: str) -> Note | None:
        path = self.folder / f"{slug}.md"
        if path.exists():
            return note_from_markdown(path.read_text(encoding="utf-8"), slug)
        canonical = await self._aliases.fetch(slug, None)
        if canonical and canonical != slug:
            return await self.get(canonical)
        return None

    async def all_notes(self) -> list[Note]:
        out: list[Note] = []
        for path in sorted(self.folder.glob("*.md")):
            note = await self.get(path.stem)
            if note is not None:
                out.append(note)
        return out

    async def match(self, query: str, top_k: int = 5) -> list[tuple[Note, float]]:
        results = await self._docs.search(query, on=["key"])
        out: list[tuple[Note, float]] = []
        for scored in results[:top_k]:
            note = await self.get(scored.document.body.slug)
            if note is not None:
                out.append((note, scored.score))
        return out

    async def search_vector(
        self, vector: list[float], top_k: int = 5
    ) -> list[tuple[Note, float]]:
        out: list[tuple[Note, float]] = []
        for item in await self._vectors.near(vector, k=top_k):
            note = await self.get(item.id)
            if note is not None:
                out.append((note, item.score))
        return out

    async def close(self) -> None:
        await self._db.close()
