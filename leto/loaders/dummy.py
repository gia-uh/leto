from ..loaders import Loader

from leto.model import Entity, Relation


class DummyLoader(Loader):
    def __init__(self, tuples: str) -> None:
        self.tuples = tuples

    def load(self):
        for line in self.tuples.split("\n"):
            e1, r, e2 = line.split("-")

            if ":" in e1:
                e1,t1 = e1.split(":")
            else:
                t1="Thing"

            if ":" in e2:
                e2,t2 = e2.split(":")
            else:
                t2="Thing"

            yield Relation(
                    label=r,
                    entity_from=Entity(name=e1, type=t1),
                    entity_to=Entity(name=e2, type=t2),
                )
