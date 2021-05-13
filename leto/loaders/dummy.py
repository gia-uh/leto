import random
from ..loaders import Loader

from leto.model import Entity, Relation


class DummyLoader(Loader):
    def __init__(self, n_tuples: int, max_index: int) -> None:
        self.n_tuples = n_tuples
        self.max_index = max_index

    def load(self):
        for _ in range(self.n_tuples):
            yield Relation(
                    label=f"relation{random.randint(0, self.max_index)}",
                    entity_from=Entity(name=f"Entity{random.randint(0, self.max_index)}", type="Entity"),
                    entity_to=Entity(name=f"Entity{random.randint(0, self.max_index)}", type="Entity"),
                )
