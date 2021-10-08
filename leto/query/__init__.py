import abc
from dataclasses import dataclass
from typing import Iterable, List

from leto.model import Entity, Relation


@dataclass
class Query(abc.ABC):
    entities: List[str]
    relations: List[str]
    attributes: List[str]


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
    def _resolve(self, query: Query) -> Iterable[Relation]:
        pass

    def resolve(self, query: Query) -> List[Relation]:
        return list(set(self._resolve(query)))


class QueryParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, query: str) -> Query:
        pass


class QueryPreprocessor(abc.ABC):
    @abc.abstractmethod
    def preprocess(self, query:Query, storage) -> Query:
        pass


def get_parsers():
    from leto.query.rules import SpanishRuleParser, EnglishRuleParser

    return [EnglishRuleParser, SpanishRuleParser]
