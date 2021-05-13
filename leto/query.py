import abc
from typing import Iterable
from .storage import Storage
from .storage.dummy import DummyStorage

from leto.model import Relation


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def query(self, query, storage: Storage) -> Iterable[Relation]:
        pass


class DummyQueryResolver(QueryResolver):
    def query(self, query, storage: DummyStorage):
        components = set(query.split())

        for r in storage.storage:
            if r.entity_from.name in components or r.label in components or r.entity_to.name in components:
                yield r
