from io import BytesIO
from leto.loaders.unstructured import SVOFromText, SVOFromFile, Language
from leto.model import Entity, Relation


def test_svo_from_text():
    loader = SVOFromText("Colombus discovered the American Continent", Language.en)
    tuples = list(loader.load())

    assert Relation("discover", Entity("Colombus", "Thing"), Entity("American_Continent", "Thing")) in tuples


def test_svo_from_file():
    text = BytesIO(b"Colombus discovered the American Continent")
    loader = SVOFromFile(text, Language.en)
    tuples = list(loader.load())

    assert Relation("discover", Entity("Colombus", "Thing"), Entity("American_Continent", "Thing")) in tuples
