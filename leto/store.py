from __future__ import annotations

from pathlib import Path

from beaver import BeaverDB, Document
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
    def __init__(self, folder: str | Path, db_path: str | Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._db = BeaverDB(str(db_path))
        self._docs = self._db.docs("notes", model=NoteDoc)   # beaver: typed collection
        self._graph = self._db.graph("links")                 # beaver: graph store
        self._vectors = self._db.vectors("embeddings")        # beaver: vector index

    def put(self, note: Note, embedding: list[float] | None = None) -> None:
        (self.folder / f"{note.slug}.md").write_text(
            note_to_markdown(note), encoding="utf-8"
        )
        self._docs.index(                                     # beaver: FTS index
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
            self._vectors.set(note.slug, embedding)           # beaver: vector set
        for target in note.links:
            if (self.folder / f"{target}.md").exists():
                self._graph.link(note.slug, target, label="relates_to")  # beaver: edge

    def get(self, slug: str) -> Note | None:
        path = self.folder / f"{slug}.md"
        if not path.exists():
            return None
        return note_from_markdown(path.read_text(encoding="utf-8"), slug)

    def match(self, query: str, top_k: int = 5) -> list[tuple[Note, float]]:
        results = self._docs.search(query, on=["title", "text"])  # beaver: FTS -> list[ScoredDocument]
        out: list[tuple[Note, float]] = []
        for scored in results[:top_k]:
            note = self.get(scored.document.body.slug)
            if note is not None:
                out.append((note, scored.score))
        return out

    def search_vector(
        self, vector: list[float], top_k: int = 5
    ) -> list[tuple[Note, float]]:
        out: list[tuple[Note, float]] = []
        for item in self._vectors.near(vector, k=top_k):      # beaver: vector near
            note = self.get(item.id)
            if note is not None:
                out.append((note, item.score))
        return out

    def all_notes(self) -> list[Note]:
        out: list[Note] = []
        for path in sorted(self.folder.glob("*.md")):
            note = self.get(path.stem)
            if note is not None:
                out.append(note)
        return out

    def neighbors(self, slug: str) -> list[Note]:
        out: list[Note] = []
        for target in self._graph.children(slug, label="relates_to"):  # beaver: children
            note = self.get(target)
            if note is not None:
                out.append(note)
        return out

    def close(self) -> None:
        self._db.close()
