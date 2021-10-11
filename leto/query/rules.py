from abc import abstractmethod
from typing import Dict
from leto.query import *
from leto.utils import get_model
from spacy import Language


class RuleBasedQueryParser(QueryParser):
    def __init__(self, *args) -> None:
        pass

    @abstractmethod
    def _get_model(self) -> Language:
        pass

    @abstractmethod
    def _get_query_hints(self) -> Dict[type, str]:
        pass

    def _make_entity(self, e):
        words = [tok for tok in e]

        while words[0].pos_ == "DET":
            words.pop(0)

        return e[: -len(words)]

    def parse(self, query: str) -> Query:
        nlp = self._get_model()
        doc = nlp(query)

        entities = [e for e in doc.ents] or [n for n in doc.noun_chunks]
        relations = [token for token in doc if token.pos_ in ["VERB", "NOUN"]]
        attributes = [token for token in doc if token.pos_ in ["NOUN", "ADJ"]]

        query_hints = self._get_query_hints()

        best_query = None
        best_query_matches = 0

        for query_type, hints in query_hints.items():
            found_hints = len([token.lemma_ for token in doc if token.lemma_ in hints])
            if found_hints > best_query_matches:
                best_query = query_type(
                    entities=entities, relations=relations, attributes=attributes
                )
                best_query_matches = found_hints

        if best_query is not None:
            return best_query

        return Query(entities=entities, relations=relations, attributes=attributes)


class SpanishRuleParser(RuleBasedQueryParser):
    def _get_model(self):
        return get_model("es_core_news_sm")

    def _get_query_hints(self) -> Dict[type, str]:
        return {
            WhatQuery: ["qué"],
            WhoQuery: ["quién"],
            WhichQuery: ["cuál"],
            WhereQuery: ["dónde"],
            HowManyQuery: ["cuánto"],
            PredictQuery: ["qué", "influir", "predecir", "cuál"],
        }


class EnglishRuleParser(RuleBasedQueryParser):
    def _get_model(self):
        return get_model("en_core_web_sm")

    def _get_query_hints(self) -> Dict[type, str]:
        return {
            WhatQuery: ["what"],
            WhoQuery: ["who"],
            WhichQuery: ["which"],
            WhereQuery: ["where"],
            HowManyQuery: ["how", "much"],
            PredictQuery: ["what", "influence", "predict", "which"],
        }
