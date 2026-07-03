from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field


class NoteKind(str, Enum):
    ENTITY = "entity"
    PROCEDURE = "procedure"


class Settlement(str, Enum):
    FLEETING = "fleeting"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    PERMANENT = "permanent"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return s.strip("-")


class Note(BaseModel):
    slug: str
    kind: NoteKind
    title: str
    body: str = ""
    settlement: Settlement = Settlement.FLEETING
    links: list[str] = Field(default_factory=list)


class ExtractedItem(BaseModel):
    kind: NoteKind
    title: str
    body: str = ""
    links: list[str] = Field(default_factory=list)


class RecalledNote(BaseModel):
    note: Note
    score: float
    via: str


class KnowledgeBlob(BaseModel):
    query: str
    facts: list[RecalledNote] = Field(default_factory=list)
    procedures: list[RecalledNote] = Field(default_factory=list)
