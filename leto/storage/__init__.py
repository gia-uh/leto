import abc
from typing import List


class Storage(abc.ABC):
    @abc.abstractmethod
    def store_tuple(self, entity_from, relation, entity_to):
        pass

    @abc.abstractproperty
    def size(self):
        pass


def get_storages() -> List[Storage]:
    from leto.storage.dummy import DummyStorage
    from leto.storage.neo4j import GraphStorage

    return [DummyStorage, GraphStorage]
