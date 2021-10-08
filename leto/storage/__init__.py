import abc
from leto.model import Entity, Relation
from typing import List, Union

from leto.query import QueryResolver


class Storage(abc.ABC):
    @abc.abstractmethod
    def store(self, entity_or_relation: Union[Entity, Relation]):
        pass

    @abc.abstractproperty
    def size(self):
        pass

    @abc.abstractmethod
    def get_query_resolver(self) -> QueryResolver:
        pass


def get_storages() -> List[Storage]:
    from leto.storage.dummy import DummyStorage
    from leto.storage.neo4j import GraphStorage

    return [GraphStorage]
