import abc
from dataclasses import dataclass
from typing import Iterable

from leto.model import Relation


@dataclass(frozen=True)
class Query(abc.ABC):
    pass


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def query(self, query: Query) -> Iterable[Relation]:
        pass
