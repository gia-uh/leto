from typing import List
from leto.loaders.structured import MultiCSVLoader
from pathlib import Path


datapath = Path(__file__).parent / "data"


def load_files(*filenames: List[str]):
    return [open(datapath / fname) for fname in filenames]


<<<<<<< HEAD
single_loader = MultiCSVLoader(files=load_files("single_file.csv"))
single_tuples = list(single_loader.load())
multi_loader = MultiCSVLoader(
    files=load_files("students.csv", "mentors.csv", "topics.csv")
)
multi_tuples = list(single_loader.load())


def test_load_entities_from_one_file():

    assert single_tuples[0]


def test_load_has_property():
    assert [
        x
        for x in multi_tuples
        if x.entity_from.type == "THING"
        and x.entity_to.type == "PROP"
        and x.label == "has_property"
    ]


def test_load_types():
    assert [
        x
        for x in multi_tuples
        if x.entity_from.type in ["THING", "PROP"]
        and x.entity_to.type == "TYPE"
        and x.label == "is_a"
    ]


def test_load_same_as():
    assert [
        x
        for x in multi_tuples
        if x.entity_from.type == "THING"
        and x.entity_to.type == "THING"
        and x.label == "same_as"
    ]


def test_load_entity():
    assert [
        x
        for x in multi_tuples
        if x.entity_from.type == "THING"
        and x.entity_to.type == "THING"
        and x.label == "is_a"
    ]


def test_load_foreign_key():
    assert [
        x
        for x in multi_tuples
        if x.entity_from.type == "THING"
        and x.entity_to.type == "THING"
        and x.label == "students_mentor"
    ]
=======
# def test_load_entities_from_one_file():
#     loader = MultiCSVLoader(files=load_files("single_file.csv"))
#     tuples = list(loader.load())

#     assert tuples[0]
>>>>>>> 6d65b1b (Update tests)
