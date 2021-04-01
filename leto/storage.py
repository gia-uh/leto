import abc
import pickle
import pathlib


class Storage(abc.ABC):
    @abc.abstractmethod
    def store_tuple(self, entity_from, relation, entity_to):
        pass

    @abc.abstractproperty
    def size(self):
        pass


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
        with open("storage.pickle", "wb") as fp:
            pickle.dump(self.storage, fp)

    def _load(self):
        if not pathlib.Path("storage.pickle").exists():
            return

        with open("storage.pickle", "rb") as fp:
            self.storage = pickle.load(fp)
