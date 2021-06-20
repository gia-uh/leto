import abc
import re
from dataclasses import dataclass
from typing import Iterable, List

from leto.model import Relation


@dataclass
class Query(abc.ABC):
    pass


@dataclass
class MatchQuery(Query):
    terms: List[str]
    include_relations: bool = False


@dataclass
class WhatQuery(Query):
    entity: str
    relation: str


@dataclass
class WhoQuery(Query):
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

        m = re.match(r"who is the (?P<relation>\w+) of (?P<entity>\w+)", query)

        if m:
            return WhoQuery(entity=m.group("entity"), relation=m.group("relation"))

        return MatchQuery(terms=list(set(query.split())))


def get_parsers():
    return [DummyQueryParser]
