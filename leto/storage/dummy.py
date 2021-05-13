from leto.model import Relation
import pickle
import pathlib
from typing import AbstractSet


from leto.storage import Storage


class DummyStorage(Storage):
    def __init__(self) -> None:
        self.storage: AbstractSet[Relation] = set()
        self._load()

    def store(self, relation):
        self.storage.add(relation)
        self._save()

    @property
    def size(self):
        return len(self.storage)

    def _save(self):
        with open("/src/data/storage.pickle", "wb") as fp:
            pickle.dump(self.storage, fp)

    def _load(self):
        if not pathlib.Path("/src/data/storage.pickle").exists():
            return

        with open("/src/data/storage.pickle", "rb") as fp:
            self.storage = pickle.load(fp)
