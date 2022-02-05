import abc
from dataclasses import dataclass
from typing import Iterable, List, Optional
from leto.model import Entity, Relation
from fuzzywuzzy import process


@dataclass
class Query(abc.ABC):
    entities: List[str]
    relations: List[str]
    attributes: List[str]
    aggregate: Optional[str] = ""
    groupby: Optional[str] = ""


@dataclass
class MatchQuery(Query):
    pass


@dataclass
class WhatQuery(Query):
    pass


@dataclass
class WhoQuery(Query):
    pass


@dataclass
class HowManyQuery(Query):
    pass


@dataclass
class WhichQuery(Query):
    pass


@dataclass
class WhereQuery(Query):
    pass


@dataclass
class PredictQuery(Query):
    pass


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def _resolve(self, query: Query, breadth: int) -> Iterable[Relation]:
        pass

    def resolve(self, query: Query, breadth: int = 0) -> List[Relation]:
        return list(set(self._resolve(query, breadth)))


class QueryParser(abc.ABC):
    def __init__(self, storage) -> None:
        from leto.storage import Storage

        self.storage: Storage = storage

    @abc.abstractmethod
    def parse(self, query: str) -> Query:
        pass


def get_parsers():
    from leto.query.rules import SpanishRuleParser, EnglishRuleParser

    return [EnglishRuleParser, SpanishRuleParser]
