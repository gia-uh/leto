from leto.query import FuzzyQuery, QueryParser, Query
from leto.storage.neo4j import GraphStorage


class FuzzyParser(QueryParser):
    def __init__(self, storage: GraphStorage) -> None:
        if not isinstance(storage, GraphStorage):
            raise ValueError(
                "Cannot use FuzzyParser without storage of type GraphStorage"
            )

        self.storage = storage

    def parse(self, query: str) -> Query:
        terms = query.split()

        return FuzzyQuery(entities=terms, relations=[], attributes=[])
