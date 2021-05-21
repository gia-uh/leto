import random
from ..loaders import Loader

from leto.model import Entity, Relation


class DummyLoader(Loader):
    def __init__(self, tuples: str) -> None:
        self.tuples = tuples

    def load(self):
        for line in self.tuples.split("\n"):
            e1, r, e2 = line.split()

            yield Relation(
                    label=r,
                    entity_from=Entity(name=e1, type="Entity"),
                    entity_to=Entity(name=e2, type="Entity"),
                )
