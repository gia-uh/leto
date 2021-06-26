from abc import abstractmethod
from typing import Dict
from leto.query import *
from spacy import Language


class RuleBasedQueryParser(QueryParser):
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

        return Entity(" ".join(tok.text for tok in words), e.label_)

    def parse(self, query: str) -> Query:
        nlp = self._get_model()
        doc = nlp(query)

        entities = [self._make_entity(e) for e in doc.ents]
        terms = [token.lemma_ for token in doc if token.pos_ in ["NOUN", "VERB"]]

        query_hints = self._get_query_hints()

        for query_type, hints in query_hints.items():
            if doc[0].lemma_ in hints:
                return query_type(entities=entities, terms=terms)

        return MatchQuery(entities=entities, terms=terms)


class SpanishRuleParser(RuleBasedQueryParser):
    def _get_model(self):
        return get_model("es_core_news_sm")

    def _get_query_hints(self) -> Dict[type, str]:
        return {
            WhatQuery: ["qué", "que"],
            WhoQuery: ["quién", "quien"],
            WhichQuery: ["cuál", "cual"],
            WhereQuery: ["dónde", "donde"],
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
        }
