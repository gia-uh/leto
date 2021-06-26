from leto.utils import Text
from ..loaders import Loader

from leto.model import Entity, Relation


class ManualLoader(Loader):
    """Load manually introduced tuples of entities (with optional types) and relations in the format:

    entity[:type] - relation - entity[:type]
    """
    def __init__(self, tuples: Text) -> None:
        self.tuples = tuples

    def load(self):
        for line in self.tuples.split("\n"):
            e1, r, e2 = line.split("-")
            e1 = e1.strip()
            r = r.strip()
            e2 = e2.strip()

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


class ExampleLoader(Loader):
    """Loads an example dataset where you can try the example queries.

*⚠️ This modifies the database permanently!*
    """
    def load(self):
        # Ontology of Revolutions
        Country = Entity("Country", "Thing")

        Cuba = Entity("Cuba", "Place", lon=25, lat=50)
        yield Relation("is_a", Cuba, Country)

        Rusia = Entity("Rusia", "Place", lon=90, lat=40)
        yield Relation("is_a", Rusia, Country)

        yield Relation(label="allied", entity_from=Cuba, entity_to=Rusia)
        yield Relation(label="allied", entity_from=Rusia, entity_to=Cuba)

        Revolution = Entity("Revolution", "Event")

        CubanRevolution = Entity("Cuban Revolution", "Event", date="1959-01-01")
        yield Relation("is_a", CubanRevolution, Revolution)
        yield Relation("has_location", CubanRevolution, Cuba)

        RusianRevolution = Entity("October Revolution", "Event", date="1918-11-17")
        yield Relation("is_a", RusianRevolution, Revolution)
        yield Relation("has_location", RusianRevolution, Rusia)

        FidelCastro = Entity("Fidel Castro", "Person", birth_date="1913-08-13")
        yield Relation("lead", FidelCastro, CubanRevolution)

        Lenin = Entity("Vladimir Illich Lenin", "Person", birth_date="1870-03-21")
        yield Relation("lead", Lenin, RusianRevolution)

        yield Relation("influence", Lenin, FidelCastro)
        yield Relation("influence", RusianRevolution, CubanRevolution)
