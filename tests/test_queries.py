from leto.query.rules import EnglishRuleParser
from leto.query import Query


def test_basic_parser():
    parser = EnglishRuleParser()
    query_str = "show info about Cuba"
    query = parser.parse(query_str)

@pytest.mark.parametrize(
    "query,result",
    [("qué es Cuba", WhatQuery(entities=[Entity("Cuba", "LOC")], terms=[]))],
)
def test_spanish_query(query, result):
    assert SpanishRuleParser().parse(query) == result
    assert isinstance(query, Query)
    assert str(query.entities[0]) == "Cuba"
