import pytest

from leto.model import Entity
from leto.query.rules import SpanishRuleParser, EnglishRuleParser
from leto.query import WhatQuery, WhoQuery, WhereQuery, WhichQuery, HowManyQuery


# @pytest.mark.parametrize(
#     "query,result",
#     [("qué es Cuba", WhatQuery(entities=[Entity("Cuba", "LOC")], terms=[]))],
# )
# def test_spanish_query(query, result):
#     assert SpanishRuleParser().parse(query) == result
