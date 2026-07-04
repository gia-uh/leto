import pytest

from leto.model import (
    Kind, Settlement, Outcome, EdgeType, Edge, Note, LAYER,
    FactPayload, ProcedurePayload, ExperiencePayload,
    slugify, retrieval_key, edge_allowed,
)


def test_slugify():
    assert slugify("  Alan Turing!  ") == "alan-turing"


def test_layers_order_fact_below_experience():
    assert LAYER[Kind.FACT] < LAYER[Kind.PROCEDURE] < LAYER[Kind.EXPERIENCE]


def test_note_requires_matching_payload():
    Note(slug="turing", kind=Kind.FACT, title="Alan Turing",
         payload=FactPayload(definition="A mathematician."))
    with pytest.raises(ValueError):
        Note(slug="x", kind=Kind.FACT, title="X",
             payload=ProcedurePayload(goal="do x"))


def test_retrieval_key_per_kind():
    fact = Note(slug="y", kind=Kind.FACT, title="Y",
                payload=FactPayload(definition="the def"))
    proc = Note(slug="do-x", kind=Kind.PROCEDURE, title="Do X",
                payload=ProcedurePayload(goal="accomplish x"))
    exp = Note(slug="e", kind=Kind.EXPERIENCE, title="E",
               payload=ExperiencePayload(situation="hit a wall", action="tried z",
                                         outcome=Outcome.FAILED, lesson="z is bad"))
    assert retrieval_key(fact) == "Y. the def"
    assert retrieval_key(proc) == "accomplish x"
    assert retrieval_key(exp) == "hit a wall"


def test_edge_direction_rules():
    assert edge_allowed(Kind.PROCEDURE, EdgeType.INVOLVES, Kind.FACT)
    assert not edge_allowed(Kind.FACT, EdgeType.INVOLVES, Kind.PROCEDURE)
    assert edge_allowed(Kind.EXPERIENCE, EdgeType.APPLIED, Kind.PROCEDURE)
    assert edge_allowed(Kind.PROCEDURE, EdgeType.STEP, Kind.PROCEDURE)
    assert not edge_allowed(Kind.EXPERIENCE, EdgeType.STEP, Kind.PROCEDURE)
    assert edge_allowed(Kind.FACT, EdgeType.RELATES_TO, Kind.FACT)
    assert not edge_allowed(Kind.FACT, EdgeType.RELATES_TO, Kind.EXPERIENCE)
