from leto.query import MatchQuery, Query, QueryResolver, WhatQuery, WhoQuery
from leto.model import Relation
import pickle
import pathlib
from typing import AbstractSet

from leto.utils import visitor
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
        with open("/home/coder/leto/data/storage.pickle", "wb") as fp:
            pickle.dump(self.storage, fp)

    def _load(self):
        if not pathlib.Path("/home/coder/leto/data/storage.pickle").exists():
            return

        with open("/home/coder/leto/data/storage.pickle", "rb") as fp:
            self.storage = pickle.load(fp)

    def get_query_resolver(self) -> QueryResolver:
        return DummyQueryResolver(self)


class DummyQueryResolver(QueryResolver):
    def __init__(self, storage: DummyStorage) -> None:
        self.storage = storage

        @visitor("query")
        def query(query: Query):
            raise NotImplementedError

        @query.register
        def query_match(query: MatchQuery):
            components = set(query.terms)

            for r in self.storage.storage:
                if r.entity_from.name in components or r.label in components or r.entity_to.name in components:
                    yield r

        @query.register
        def query_what(query: WhatQuery):
            for r in self.storage.storage:
                if r.entity_from.name == query.entity and r.label == query.relation:
                    yield r

        @query.register
        def query_who(query: WhoQuery):
            for r in self.storage.storage:
                if r.entity_to.name == query.entity and r.label == query.relation:
                    yield r

        self._query = query

    def resolve(self, query: Query):
        return self._query(query=query)
