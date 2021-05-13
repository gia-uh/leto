import abc
from dataclasses import dataclass
from typing import Iterable, List

from leto.model import Relation


@dataclass(frozen=True)
class Query(abc.ABC):
    pass


@dataclass(frozen=True)
class MatchQuery(Query):
    terms: List[str]


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def query(self, query: Query) -> Iterable[Relation]:
        pass


class QueryParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, query:str) -> Query:
        pass


class DummyQueryParser(QueryParser):
    def parse(self, query: str) -> Query:
        return MatchQuery(terms=list(set(query.split())))


def get_parsers():
    return [DummyQueryParser]
