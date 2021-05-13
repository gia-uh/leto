import pickle
import pathlib


from leto.storage import Storage


class DummyStorage(Storage):
    def __init__(self) -> None:
        self.storage = set()
        self._load()

    def store_tuple(self, entity_from, relation, entity_to):
        self.storage.add((entity_from, relation, entity_to))
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
