from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Kind(str, Enum):
    FACT = "fact"
    PROCEDURE = "procedure"
    EXPERIENCE = "experience"


LAYER: dict[Kind, int] = {Kind.FACT: 0, Kind.PROCEDURE: 1, Kind.EXPERIENCE: 2}


class Settlement(str, Enum):
    FLEETING = "fleeting"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    PERMANENT = "permanent"


class Outcome(str, Enum):
    WORKED = "worked"
    FAILED = "failed"


class FactPayload(BaseModel):
    definition: str = ""


class ProcedurePayload(BaseModel):
    goal: str = ""


class ExperiencePayload(BaseModel):
    situation: str = ""
    action: str = ""
    outcome: Outcome = Outcome.WORKED
    lesson: str = ""


_PAYLOAD_FOR: dict[Kind, type] = {
    Kind.FACT: FactPayload,
    Kind.PROCEDURE: ProcedurePayload,
    Kind.EXPERIENCE: ExperiencePayload,
}


class EdgeType(str, Enum):
    RELATES_TO = "relates_to"
    INVOLVES = "involves"
    STEP = "step"
    DEPENDS_ON = "depends_on"
    APPLIED = "applied"
    ABOUT = "about"
    FOLLOWS = "follows"
    SUPERSEDES = "supersedes"
    CONTRADICTS = "contradicts"


# (allowed from-kinds, allowed to-kinds) per edge type. All respect the
# downstream rule (to-layer <= from-layer), also asserted in edge_allowed.
EDGE_RULES: dict[EdgeType, tuple[set[Kind], set[Kind]]] = {
    EdgeType.RELATES_TO: ({Kind.FACT, Kind.EXPERIENCE}, {Kind.FACT, Kind.EXPERIENCE}),
    EdgeType.INVOLVES: ({Kind.PROCEDURE}, {Kind.FACT}),
    EdgeType.STEP: ({Kind.PROCEDURE}, {Kind.PROCEDURE}),
    EdgeType.DEPENDS_ON: ({Kind.PROCEDURE}, {Kind.PROCEDURE}),
    EdgeType.APPLIED: ({Kind.EXPERIENCE}, {Kind.PROCEDURE}),
    EdgeType.ABOUT: ({Kind.EXPERIENCE}, {Kind.FACT}),
    EdgeType.FOLLOWS: ({Kind.EXPERIENCE}, {Kind.EXPERIENCE}),
    EdgeType.SUPERSEDES: ({Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE},
                          {Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE}),
    EdgeType.CONTRADICTS: ({Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE},
                           {Kind.FACT, Kind.PROCEDURE, Kind.EXPERIENCE}),
}

ORDERED_EDGES: set[EdgeType] = {EdgeType.STEP}

# same-kind-only edges (checked in edge_allowed)
_SAME_KIND_ONLY: set[EdgeType] = {
    EdgeType.SUPERSEDES, EdgeType.CONTRADICTS, EdgeType.RELATES_TO,
}


def edge_allowed(from_kind: Kind, type: EdgeType, to_kind: Kind) -> bool:
    froms, tos = EDGE_RULES[type]
    if from_kind not in froms or to_kind not in tos:
        return False
    if type in _SAME_KIND_ONLY and from_kind is not to_kind:
        return False
    return LAYER[to_kind] <= LAYER[from_kind]   # downstream rule: never point up


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return s.strip("-")


class Edge(BaseModel):
    target: str
    type: EdgeType
    order: int | None = None


class Note(BaseModel):
    slug: str
    kind: Kind
    title: str
    settlement: Settlement = Settlement.FLEETING
    sources: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    valid_from: str | None = None
    valid_to: str | None = None          # None = INF (still true)
    recorded_at: str | None = None       # stamped by the store on write
    promoted_from: list[str] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    payload: FactPayload | ProcedurePayload | ExperiencePayload

    @model_validator(mode="after")
    def _payload_matches_kind(self) -> "Note":
        if not isinstance(self.payload, _PAYLOAD_FOR[self.kind]):
            raise ValueError(
                f"payload {type(self.payload).__name__} does not match kind {self.kind}")
        return self


def retrieval_key(note: Note) -> str:
    if note.kind is Kind.FACT:
        return f"{note.title}. {note.payload.definition}".strip()
    if note.kind is Kind.PROCEDURE:
        return note.payload.goal or note.title
    return note.payload.situation or note.title   # experience
