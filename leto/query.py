import abc
import re
from dataclasses import dataclass
from typing import Iterable, List

from leto.model import Relation


@dataclass(frozen=True)
class Query(abc.ABC):
    pass


@dataclass(frozen=True)
class MatchQuery(Query):
    terms: List[str]


@dataclass
class WhatQuery(Query):
    entity: str
    relation: str


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def resolve(self, query: Query) -> Iterable[Relation]:
        pass


class QueryParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, query:str) -> Query:
        pass


class DummyQueryParser(QueryParser):
    def parse(self, query: str) -> Query:
        m = re.match(r"what is the (?P<relation>\w+) of (?P<entity>\w+)", query)

        if m:
            return WhatQuery(entity=m.group("entity"), relation=m.group("relation"))

        return MatchQuery(terms=list(set(query.split())))


def get_parsers():
    return [DummyQueryParser]
