import abc
import uuid
from typing import Iterable, List
from leto.model import Entity, Relation
import datetime


class Loader(abc.ABC):
    @abc.abstractmethod
    def _load(self) -> Iterable[Relation]:
        pass

    def load(self, **metadata) -> Iterable[Relation]:
        entities = set()

        for relation in self._load():
            yield relation
            entities.add(relation.entity_from)
            entities.add(relation.entity_to)

        metadata = Entity(f"Meta-{str(uuid.uuid4())}", "_METADATA", created_on=datetime.datetime.now().astimezone(None).isoformat(), **metadata)

        for entity in entities:
            yield Relation("__metadata__", entity, metadata)

    @classmethod
    def title(cls):
        return cls.__name__


def get_loaders() -> List[Loader]:
    from .unstructured import SVOFromFile, SVOFromText
    from .dummy import ManualLoader, ExampleLoader
    from .structured import MultiCSVLoader
    from .wikipedia import WikipediaLoader

    return [
        ExampleLoader,
        ManualLoader,
        MultiCSVLoader,
        SVOFromFile,
        SVOFromText,
        WikipediaLoader,
    ]
