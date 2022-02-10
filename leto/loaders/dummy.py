from leto.utils import Text
from ..loaders import Loader

from leto.model import Entity, Relation, Source
import random


class ManualLoader(Loader):
    """
    Load manually introduced tuples of entities (with optional types) and relations in the format:

        entity[:type] - relation - entity[:type]
    """

    @classmethod
    def title(cls):
        return "Manually enter tuples"

    def __init__(self, tuples: Text) -> None:
        self.tuples = tuples

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="manual", loader="ManualLoader", **metadata)

    def _load(self):
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
    """
    Loads an example dataset where you can try the example queries.

    *⚠️ This modifies the database permanently!*
    """

    @classmethod
    def title(cls):
        return "Synthetic toy examples"

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="manual", loader="ExampleLoader", **metadata)

    def _load(self):
        r = random.Random(0)

        # Ontology of Revolutions
        Country = Entity("Country", "Thing")
        yield Country

        Cuba = Entity("Cuba", "Place", lon=-77.78, lat=21.52)
        yield Cuba
        yield Relation("is_a", Cuba, Country)

        Russia = Entity("Russia", "Place", lon=105.31, lat=61.52)
        yield Russia
        yield Relation("is_a", Russia, Country)

        Revolution = Entity("Revolution", "Event")
        yield Revolution

        CubanRevolution = Entity("Cuban Revolution", "Event", date="1959-01-01")
        yield CubanRevolution
        yield Relation("is_a", CubanRevolution, Revolution)
        yield Relation("has_location", CubanRevolution, Cuba)

        RusianRevolution = Entity("October Revolution", "Event", date="1918-11-17")
        yield RusianRevolution
        yield Relation("is_a", RusianRevolution, Revolution)
        yield Relation("has_location", RusianRevolution, Russia)

        FidelCastro = Entity("Fidel Castro", "Person", birth_date="1913-08-13")
        yield FidelCastro
        yield Relation("leader_of", FidelCastro, CubanRevolution)

        Lenin = Entity("Vladimir Illich Lenin", "Person", birth_date="1870-03-21")
        yield Lenin
        yield Relation("leader_of", Lenin, RusianRevolution)

        yield Relation("influenced_by", FidelCastro, Lenin)
        yield Relation("inspired_by", CubanRevolution, RusianRevolution)

        # Jobs data
        DataScientist = Entity("DataScientist", "Thing", abstract=True)
        yield DataScientist

        for _ in range(10):
            firstname = r.choice(["Mary", "Tom", "Pete", "John", "Ana", "Susan"])
            lastname = r.choice(["Johnson", "Smith", "Jackson", "Brooks", "Anderson"])
            age = r.randint(20, 50)
            gender = r.choice(["male", "female"])

            person = Entity(
                firstname + lastname,
                "Person",
                firstname=firstname,
                lastname=lastname,
                age=age,
                gender=gender,
            )
            yield person
            yield Relation(
                "is_a", person, DataScientist, salary=r.randint(1, 10) * 1000
            )
