from leto.query import Query, QueryResolver
from leto.model import Relation
import pickle
import pathlib
from typing import AbstractSet


from leto.storage import Storage


class DummyStorage(Storage):
    def __init__(self) -> None:
        self.storage: AbstractSet[Relation] = set()
        self._load()

    def store(self, relation):
        self.storage.add(relation)
        self._save()

    @property
    def size(self):
        return len(self.storage)

    def _save(self):
        with open("/src/data/storage.pickle", "wb") as fp:
            pickle.dump(self.storage, fp)

    def _load(self):
        if not pathlib.Path("/src/data/storage.pickle").exists():
            return

        with open("/src/data/storage.pickle", "rb") as fp:
            self.storage = pickle.load(fp)

    def get_query_resolver(self) -> QueryResolver:
        return DummyQueryResolver(self)


class DummyQueryResolver(QueryResolver):
    def __init__(self, storage: DummyStorage) -> None:
        self.storage = storage

    def query(self, query: Query):
        components = set(query.split())

        for r in self.storage.storage:
            if r.entity_from.name in components or r.label in components or r.entity_to.name in components:
                yield r
