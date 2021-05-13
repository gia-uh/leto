import abc
from .storage import Storage
from .storage.dummy import DummyStorage


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def query(self, query, storage: Storage):
        pass


class DummyQueryResolver(QueryResolver):
    def query(self, query, storage: DummyStorage):
        components = set(query.split())

        for e1, r, e2 in storage.storage:
            if e1 in components or r in components or e2 in components:
                yield (e1, r, e2)
