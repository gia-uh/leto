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

    def _match(self, query: str, candidates: List[str]):
        matches = []
        patterns = []

        for candidate in candidates:
            error = max(1, min(5, int(0.2 * len(candidate))))

            try:
                re = fr"(?e)(?:\s{candidate.lower()}\s){{e<={error}}}"
                best_match = regex.search(re, query)

                if best_match is not None:
                    span = best_match.span()
                    pattern = query[span[0] : span[1]].strip()

                    matches.append(candidate)
                    patterns.append(pattern)
                    query = query[: span[0]] + query[span[1] :]

                    if not query.startswith(" "):
                        query = " " + query

                    if not query.endswith(" "):
                        query = query + " "

            except regex.error:
                pass

        return query, matches, patterns

    def parse(self, query: str) -> Query:
        query = " " + " ".join(query.lower().split()) + " "

        all_labels = self.storage.get_entity_types()
        all_entities = sorted(self.storage.get_entity_names(), key=len, reverse=True)
        all_relations = self.storage.get_relationship_types()
        all_attributes = self.storage.get_attribute_types()

        query, labels, patterns = self._match(query, all_labels)
        query, entities, _ = self._match(query, all_entities)
        query, relations, _ = self._match(query, all_relations)
        query, attributes, _ = self._match(query, all_attributes)

        true_labels = []
        ignored_labels = []

        for label, pattern in zip(labels, patterns):
            if pattern.startswith("~"):
                ignored_labels.append(label)
            else:
                true_labels.append(label)

        return Query(true_labels, entities, relations, attributes, ignored_labels)
