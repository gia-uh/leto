import abc
from leto.utils import get_model
from dataclasses import dataclass
from typing import Iterable, List

from leto.model import Entity, Relation


@dataclass
class Query(abc.ABC):
    pass


@dataclass
class MatchQuery(Query):
    entities: List[Entity] = None
    terms: List[str] = None


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


@dataclass
class WhichQuery(Query):
    entities: List[Entity]
    terms: List[str]


class QueryResolver(abc.ABC):
    @abc.abstractmethod
    def resolve(self, query: Query) -> Iterable[Relation]:
        pass


class QueryParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, query:str) -> Query:
        pass


class RuleBasedQueryParser(QueryParser):
    def parse(self, query: str) -> Query:
        nlp = get_model("es_core_news_sm")
        doc = nlp(query)

        entities = [Entity(e.text, e.label_) for e in doc.ents]
        terms = [token.lemma_ for token in doc if token.pos_ in ["NOUN", "VERB"]]

        if doc[0].lemma_ == "qué":
            return WhatQuery(entities=entities, terms=terms)

        if doc[0].lemma_ == "quién":
            return WhoQuery(entities=entities, terms=terms)

        if doc[0].lemma_ == "cuál":
            return WhichQuery(entities=entities, terms=terms)

        if doc[0].lemma_ in ["cuánto","cuántos"]:
            return HowManyQuery(entities=entities, terms=terms)

        return MatchQuery(entities=entities, terms=terms)



def get_parsers():
    return [RuleBasedQueryParser]
