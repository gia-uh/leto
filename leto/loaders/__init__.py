import abc
import uuid
from typing import Iterable, List, Union
from leto.model import Entity, Relation, Source
import datetime


class Loader(abc.ABC):
    @abc.abstractmethod
    def _load(self) -> Iterable[Relation]:
        pass

    @abc.abstractmethod
    def _get_source(self, name, **metadata) -> Source:
        pass

    def load(self, **metadata) -> Iterable[Union[Entity, Relation]]:
        entities = set()

        for entity_relation in self._load():
            if isinstance(entity_relation, Entity):
                entities.add(entity_relation)
            else:
                entities.add(entity_relation.entity_from)
                entities.add(entity_relation.entity_to)

            yield entity_relation

        metadata = self._get_source(
            str(uuid.uuid4()),
            created_on=datetime.datetime.now().astimezone(None).isoformat(),
            **metadata,
        )

        for entity in entities:
            yield Relation("has_source", entity, metadata)

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
        CSVLoader,
        MultiCSVLoader,
        SVOFromFile,
        SVOFromText,
        WikipediaLoader,
    ]
