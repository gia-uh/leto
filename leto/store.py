from __future__ import annotations

from pathlib import Path

from beaver import AsyncBeaverDB, Document
from pydantic import BaseModel

from leto.markdown import note_from_markdown, note_to_markdown
from leto.model import Note


class NoteDoc(BaseModel):
    slug: str
    title: str
    text: str
    kind: str
    settlement: str


class NoteStore:
    """Async, markdown-canonical note store indexed in beaver. The `.md` file
    is the source of truth; beaver holds derived FTS + vector + graph + alias
    indices. Construct with `await NoteStore.open(folder, db_path)` (beaver's
    connect is async)."""

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
        self._docs = self._db.docs("notes", model=NoteDoc)     # beaver: typed collection
        self._vectors = self._db.vectors("embeddings")          # beaver: vector index
        self._graph = self._db.graph("links")                   # beaver: graph store
        self._aliases = self._db.dict("aliases")                # beaver: alias map
        return self

    async def put(self, note: Note, embedding: list[float] | None = None) -> None:
        (self.folder / f"{note.slug}.md").write_text(
            note_to_markdown(note), encoding="utf-8"
        )
        await self._docs.index(                                 # beaver: FTS index
            document=Document(
                id=note.slug,
                body=NoteDoc(
                    slug=note.slug,
                    title=note.title,
                    text=note.body,
                    kind=note.kind.value,
                    settlement=note.settlement.value,
                ),
            )
        )
        if embedding is not None:
            await self._vectors.set(note.slug, embedding)       # beaver: vector set
        for target in note.links:
            if (self.folder / f"{target}.md").exists():
                await self._graph.link(note.slug, target, label="relates_to")  # beaver: edge

    async def get(self, slug: str) -> Note | None:
        path = self.folder / f"{slug}.md"
        if path.exists():
            return note_from_markdown(path.read_text(encoding="utf-8"), slug)
        canonical = await self._aliases.fetch(slug, None)       # beaver: alias fetch
        if canonical and canonical != slug:
            return await self.get(canonical)
        return None

    async def set_alias(self, old_slug: str, canonical_slug: str) -> None:
        await self._aliases.set(old_slug, canonical_slug)       # beaver: alias set

    async def delete(self, slug: str) -> None:
        path = self.folder / f"{slug}.md"
        if path.exists():
            path.unlink()
        await self._docs.drop(slug)                             # beaver: drop doc
        await self._vectors.delete(slug)                        # beaver: drop vector

    async def match(self, query: str, top_k: int = 5) -> list[tuple[Note, float]]:
        results = await self._docs.search(query, on=["title", "text"])  # beaver: FTS
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
        for item in await self._vectors.near(vector, k=top_k):  # beaver: vector near
            note = await self.get(item.id)
            if note is not None:
                out.append((note, item.score))
        return out

    async def all_notes(self) -> list[Note]:
        out: list[Note] = []
        for path in sorted(self.folder.glob("*.md")):
            note = await self.get(path.stem)
            if note is not None:
                out.append(note)
        return out

    async def neighbors(self, slug: str) -> list[Note]:
        out: list[Note] = []
        async for target in self._graph.children(slug, label="relates_to"):  # beaver: children
            note = await self.get(target)
            if note is not None:
                out.append(note)
        return out

    async def redirect_edges(self, from_slug: str, to_slug: str) -> None:
        parents = [p async for p in self._graph.parents(from_slug, label="relates_to")]  # beaver: parents
        for parent in parents:
            await self._graph.unlink(parent, from_slug, label="relates_to")   # beaver: unlink
            await self._graph.link(parent, to_slug, label="relates_to")       # beaver: link

    async def close(self) -> None:
        await self._db.close()
