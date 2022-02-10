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
    def get_relationship_types(self) -> List[str]:
        pass

    @abc.abstractmethod
    def get_attribute_types(self) -> List[str]:
        pass

    @abc.abstractmethod
    def get_entity_names(self) -> List[str]:
        pass

    @abc.abstractmethod
    def get_entity_types(self) -> List[str]:
        pass

    @abc.abstractmethod
    def get_query_resolver(self) -> QueryResolver:
        pass

    @abc.abstractmethod
    def clear(self) -> None:
        pass


def get_storages() -> List[Storage]:
    from leto.storage.dummy import DummyStorage
    from leto.storage.neo4j_storage import Neo4jStorage

    return [Neo4jStorage]
