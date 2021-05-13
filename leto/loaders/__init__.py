import abc
from typing import List


class Loader(abc.ABC):
    @abc.abstractmethod
    def load(self):
        pass


def get_loaders() -> List[Loader]:
    from .unstructured import SVOFromFile, SVOFromText
    from .dummy import DummyLoader
    from .structured import CsvLoader

    return [DummyLoader, CsvLoader, SVOFromFile, SVOFromText]
