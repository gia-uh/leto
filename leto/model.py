from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    name: str
    type: str

    def __str__(self) -> str:
        return f"{self.name}:{self.type}"


@dataclass(frozen=True)
class Relation:
    label: str
    entity_from: Entity
    entity_to: Entity

    def __str__(self) -> str:
        return f"({self.entity_from}) -[{self.label}]-> ({self.entity_to})"
