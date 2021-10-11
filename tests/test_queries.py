from leto.query.rules import EnglishRuleParser
from leto.query import Query


def test_basic_parser():
    parser = EnglishRuleParser()
    query_str = "show info about Cuba"
    query = parser.parse(query_str)

    assert isinstance(query, Query)
    assert str(query.entities[0]) == "Cuba"