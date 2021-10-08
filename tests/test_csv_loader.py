from typing import List
from leto.loaders.structured import MultiCSVLoader
from pathlib import Path


datapath = Path(__file__).parent / "data"


def load_files(*filenames: List[str]):
    return [open(datapath / fname) for fname in filenames]


def test_load_entities_from_one_file():
    loader = MultiCSVLoader(files=load_files("single_file.csv"))
    tuples = list(loader.load())

    assert tuples[0]