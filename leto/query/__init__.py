import abc
from leto.utils import get_model
from dataclasses import dataclass
from typing import Iterable, List

from leto.model import Entity, Relation


@dataclass
class Query(abc.ABC):
    pass


@dataclass
class FuzzyQuery(Query):
    entities: List[str]
    relations: List[str]
    attributes: List[str]


@dataclass
class MatchQuery(Query):
    entities: List[Entity]
    terms: List[str]


@dataclass
class WhatQuery(Query):
    entities: List[Entity]
    terms: List[str]


@dataclass
class WhoQuery(Query):
    entities: List[Entity]
    terms: List[str]


@dataclass
class HowManyQuery(Query):
    entities: List[Entity]
    terms: List[str]

    @property
    def field(self):
        return self.terms[0]

    @property
    def attributes(self):
        return self.terms[1:]


@dataclass
class WhichQuery(Query):
    entities: List[Entity]
    terms: List[str]


@dataclass
class WhereQuery(Query):
    entities: List[Entity]
    terms: List[str]


@dataclass
class PredictQuery(Query):
    entities: List[Entity]
    terms: List[str]


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def _resolve_query(self, query: Query) -> Iterable[Relation]:
        pass

    def resolve(self, query: Query) -> List[Relation]:
        return list(set(self._resolve_query(query)))


class QueryParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, query: str) -> Query:
        pass


def get_parsers():
    from leto.query.rules import SpanishRuleParser, EnglishRuleParser
    from leto.query.fuzzy import FuzzyParser

    return [EnglishRuleParser, SpanishRuleParser]
