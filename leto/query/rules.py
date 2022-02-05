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
                re = fr"(?e)(\s{candidate.lower()}\s){{e<={error}}}"
                best_match = regex.search(re, query)

                if best_match is not None:
                    matches.append(candidate)
                    span = best_match.span()
                    query = query[: span[0]] + query[span[1] :]
            except regex.error:
                pass

        return query, matches

    def parse(self, query: str) -> Query:
        # nlp = get_model()
        # doc = nlp(query)

        query = " " + " ".join(query.lower().split()) + " "

        # noun_chunks = set(chunk.text for chunk in doc.noun_chunks)

        all_entities = sorted(self.storage.get_entity_names(), key=len, reverse=True)
        all_relations = self.storage.get_relationship_types()
        all_attributes = self.storage.get_attribute_types()

        query, entities = self._match(query, all_entities)
        query, relations = self._match(query, all_relations)
        query, attributes = self._match(query, all_attributes)

        return Query(entities, relations, attributes)

        aggregate = None
        groupby = None

        entities = []  # [e for e in doc.ents] or [n for n in doc.noun_chunks]
        relations = []  # [token for token in doc if token.pos_ in ["VERB", "NOUN"]]
        attributes = (
            []
        )  # [token for token in doc if token.pos_ in ["NOUN", "ADJ"] and token.text != "much"]

        for entity in storage.entities:
            if entity.lower() in query.lower():
                entities.append(entity)

        for rel in storage.relationships:
            if rel.replace("_", " ").lower() in query.lower():
                relations.append(rel)

        for attr in storage.attributes:
            if attr.replace("_", " ").lower() in query.lower():
                attributes.append(attr)

        for keyword in self.AGG_KEYWORDS:
            if keyword in query:
                aggregate = keyword

        for keyword in self.GROUP_KEYWORDS:
            if keyword in query:
                groupby = keyword

        # query_hints = self._get_query_hints()

        # best_query = None
        # best_query_matches = 0

        # for query_type, hints in query_hints.items():
        #     found_hints = len([token.lemma_ for token in doc if token.lemma_ in hints])
        #     if found_hints > best_query_matches:
        #         best_query = query_type(
        #             entities=entities, relations=relations, attributes=attributes
        #         )
        #         best_query_matches = found_hints

        # if best_query is not None:
        #     return best_query

        return Query(
            entities=entities,
            relations=relations,
            attributes=attributes,
            aggregate=aggregate,
            groupby=groupby,
        )


class SpanishRuleParser(RuleBasedQueryParser):
    def _get_model(self):
        return get_model("es_core_news_sm")


class EnglishRuleParser(RuleBasedQueryParser):
    def _get_model(self):
        return get_model("en_core_web_sm")
