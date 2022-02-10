from abc import abstractmethod
from typing import Dict
import regex

from leto.query import *
from leto.utils import get_model
from spacy import Language
from fuzzywuzzy import fuzz


class RuleBasedQueryParser(QueryParser):
    AGG_KEYWORDS = ["mean", "sum"]
    GROUP_KEYWORDS = ["yearly", "monthly"]

    @abstractmethod
    def _get_model(self) -> Language:
        pass

    def _make_entity(self, e):
        words = [tok for tok in e]

        while words[0].pos_ == "DET":
            words.pop(0)

        return e[: -len(words)]

    def _match(self, query: str, candidates: List[str]):
        matches = []

        for candidate in candidates:
            error = max(1, min(5, int(0.2 * len(candidate))))

            try:
                re = fr"(?e)(?:\s{candidate.lower()}\s){{e<={error}}}"
                best_match = regex.search(re, query)

                if best_match is not None:
                    matches.append(candidate)
                    span = best_match.span()
                    query = query[: span[0]] + query[span[1] :]

                    if not query.startswith(" "):
                        query = " " + query

                    if not query.endswith(" "):
                        query = query + " "

            except regex.error:
                pass

        return query, matches

    def parse(self, query: str) -> Query:
        query = " " + " ".join(query.lower().split()) + " "

        all_labels = self.storage.get_entity_types()
        all_entities = sorted(self.storage.get_entity_names(), key=len, reverse=True)
        all_relations = self.storage.get_relationship_types()
        all_attributes = self.storage.get_attribute_types()

        _, labels = self._match(query, all_labels)
        query, entities = self._match(query, all_entities)
        query, relations = self._match(query, all_relations)
        query, attributes = self._match(query, all_attributes)

        return Query(labels, entities, relations, attributes)


class SpanishRuleParser(RuleBasedQueryParser):
    def _get_model(self):
        return get_model("es_core_news_sm")


class EnglishRuleParser(RuleBasedQueryParser):
    def _get_model(self):
        return get_model("en_core_web_sm")
