import abc
from dataclasses import dataclass
from typing import Iterable, List, Optional
from leto.model import Entity, Relation
from fuzzywuzzy import process


@dataclass
class Query(abc.ABC):
    labels: List[str]
    entities: List[str]
    relations: List[str]
    attributes: List[str]
    ignored_labels: List[str] = None

    def mentions(
        self,
        *,
        label: str = None,
        entity: str = None,
        relation: str = None,
        attribute: str = None
    ):
        if label is not None and label not in self.labels:
            return False

        if entity is not None and entity not in self.entities:
            return False

        if relation is not None and relation not in self.relations:
            return False

        if attribute is not None and attribute not in self.attributes:
            return False

        return True


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def _resolve(
        self, query: Query, breadth: int, max_entities: int
    ) -> Iterable[Relation]:
        pass

    def resolve(
        self, query: Query, breadth: int = 1, max_entities: int = -1
    ) -> List[Relation]:
        return list(set(self._resolve(query, breadth, max_entities)))


class QueryParser(abc.ABC):
    def __init__(self, storage) -> None:
        from leto.storage import Storage

        self.storage: Storage = storage

    @abc.abstractmethod
    def parse(self, query: str) -> Query:
        pass


def get_parsers():
    from leto.query.rules import RuleBasedQueryParser

    return [RuleBasedQueryParser]
