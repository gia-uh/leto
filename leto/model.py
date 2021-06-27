class Entity:
    name: str
    type: str

    def __init__(self, name: str, type: str, **kwargs) -> None:
        self.name = name
        self.type = type
        self.attrs = kwargs.copy()

    def __getattr__(self, k):
        return self.attrs[k]

    def __str__(self) -> str:
        return f"{self.name}:{self.type}"

    def __repr__(self):
        return str(self)

    def __eq__(self, o: object) -> bool:
        return str(self) == str(o)

    def __hash__(self) -> int:
        return hash(str(self))

    def get(self, att):
        return self.properties.get(att)


class Relation:
    label: str
    entity_from: Entity
    entity_to: Entity

    def __init__(
        self, label: str, entity_from: Entity, entity_to: Entity, **kwargs
    ) -> None:
        self.label = label
        self.entity_from = entity_from
        self.entity_to = entity_to
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self) -> str:
        return f"({self.entity_from}) -[{self.label}]-> ({self.entity_to})"

    def __repr__(self):
        return str(self)

    def __eq__(self, o: object) -> bool:
        return str(self) == str(o)

    def __hash__(self) -> int:
        return hash(str(self))
