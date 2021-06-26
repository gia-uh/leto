from ..loaders import Loader

from leto.model import Entity, Relation


class ManualLoader(Loader):
    """Load manually introduced tuples of entities (with optional types) and relations in the format:

    entity[:type] - relation - entity[:type]
    """

    def __init__(self, tuples: str) -> None:
        self.tuples = tuples

    def load(self):
        for line in self.tuples.split("\n"):
            e1, r, e2 = line.split("-")
            e1 = e1.strip()
            r = r.strip()
            e2 = e2.strip()

            if ":" in e1:
                e1, t1 = e1.split(":")
            else:
                t1 = "Thing"

            if ":" in e2:
                e2, t2 = e2.split(":")
            else:
                t2 = "Thing"

            yield Relation(
                label=r,
                entity_from=Entity(name=e1, type=t1),
                entity_to=Entity(name=e2, type=t2),
            )


class ExampleLoader(Loader):
    """Loads an example dataset of countries and important events that have happened.
    """

    def load(self):
        Cuba = Entity("Cuba", "Place", lon=25, lat=50)
        Rusia = Entity("Rusia", "Place", lon=90, lat=40)

        yield Relation(label="allied", entity_from=Cuba, entity_to=Rusia)
        yield Relation(label="allied", entity_from=Rusia, entity_to=Cuba)
