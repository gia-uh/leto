from leto.query.rules import EnglishRuleParser, SpanishRuleParser
from leto.query import Query, WhatQuery
from leto.model import Entity
import pytest


def test_basic_parser():
    parser = EnglishRuleParser()
    query_str = "show info about Cuba"
    query = parser.parse(query_str)


@pytest.mark.parametrize(
    "query,result",
    [("qué es Cuba", WhatQuery(entities=["Cuba"], relations=[], attributes=[]))],
)
def test_spanish_query(query, result):
    query_result = SpanishRuleParser().parse(query)
    assert query_result == result
    assert isinstance(query_result, Query)
    assert str(query_result.entities[0]) == "Cuba"
