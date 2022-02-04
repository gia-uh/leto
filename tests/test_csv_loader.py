from typing import List
from leto.loaders.structured import CSVLoader
from pathlib import Path

from leto.model import Entity, Relation


datapath = Path(__file__).parent / "data"


def test_load_single_entities():
    loader = CSVLoader(path=datapath / "single_entities.csv")
    tuples = list(loader.load())

    assert len(tuples) == 6
    assert isinstance(tuples[0], Entity)
    assert tuples[0].name == "Tony Stark"
    assert tuples[0].type == "Person"
    assert tuples[0].age == 35

    assert isinstance(tuples[1], Entity)
    assert tuples[1].name == "Peter Parker"
    assert tuples[1].type == "Person"
    assert tuples[1].height == 175.3

    assert isinstance(tuples[2], Entity)
    assert tuples[2].name == "Mary Jane Watson"
    assert tuples[2].type == "Person"
    assert tuples[2].weight == 58.9


def test_load_two_entities():
    loader = CSVLoader(path=datapath / "two_entities.csv")
    tuples = list(loader.load())

    assert len(tuples) == 15
    assert isinstance(tuples[0], Entity)
    assert tuples[0].name == "inventor"
    assert tuples[0].type == "Profession"

    assert isinstance(tuples[3], Entity)
    assert tuples[3].name == "Tony Stark"
    assert tuples[3].type == "Person"

    assert isinstance(tuples[4], Relation)
    assert tuples[4].label == "has_profession"
    assert tuples[4].entity_from.name == "Tony Stark"
    assert tuples[4].entity_to.name == "inventor"


def test_load_three_entities():
    loader = CSVLoader(path=datapath / "three_entities.csv")
    tuples = list(loader.load())

    assert len(tuples) == 24
    assert isinstance(tuples[0], Entity)
    assert tuples[0].name == "inventor"
    assert tuples[0].type == "Profession"

    assert isinstance(tuples[3], Entity)
    assert tuples[3].name == "Avengers"
    assert tuples[3].type == "Team"

    assert isinstance(tuples[6], Entity)
    assert tuples[6].name == "Tony Stark"
    assert tuples[6].type == "Person"

    assert isinstance(tuples[7], Relation)
    assert tuples[7].label == "has_profession"
    assert tuples[7].entity_from.name == "Tony Stark"
    assert tuples[7].entity_to.name == "inventor"

    assert isinstance(tuples[8], Relation)
    assert tuples[8].label == "has_team"
    assert tuples[8].entity_from.name == "Tony Stark"
    assert tuples[8].entity_to.name == "Avengers"


def test_implicit_entities():
    loader = CSVLoader(path=datapath / "implicit_entities.csv")
    tuples = list(loader.load())

    assert len(tuples) == 26

    assert isinstance(tuples[6], Entity)
    assert tuples[6].type == "Fact"
    assert tuples[6].year == 2020
    assert tuples[6].missions == 15

    assert isinstance(tuples[7], Relation)
    assert tuples[7].label == "has_team"
    assert tuples[7].entity_to.name == "Avengers"
