<<<<<<< HEAD
import pytest

from leto.model import Entity
from leto.query.rules import SpanishRuleParser, EnglishRuleParser
from leto.query import WhatQuery, WhoQuery, WhereQuery, WhichQuery, HowManyQuery


@pytest.mark.parametrize(
    "query,result",
    [("qué es Cuba", WhatQuery(entities=[Entity("Cuba", "LOC")], terms=[]))],
)
def test_spanish_query(query, result):
    assert SpanishRuleParser().parse(query) == result
=======
from leto.query.rules import EnglishRuleParser
from leto.query import Query


def test_basic_parser():
    parser = EnglishRuleParser()
    query_str = "show info about Cuba"
    query = parser.parse(query_str)

    assert isinstance(query, Query)
    assert str(query.entities[0]) == "Cuba"
>>>>>>> d616cde (Add test)
