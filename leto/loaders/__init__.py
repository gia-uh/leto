import abc
from typing import Iterable, List
from leto.model import Relation


class Loader(abc.ABC):
    @abc.abstractmethod
    def load(self) -> Iterable[Relation]:
        pass


def get_loaders() -> List[Loader]:
    from .unstructured import SVOFromFile, SVOFromText
    from .dummy import ManualLoader, ExampleLoader
    from .structured import CsvLoader

    return [ExampleLoader, ManualLoader, CsvLoader, SVOFromFile, SVOFromText]
