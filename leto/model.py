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
    sources: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


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


class MergedGroup(BaseModel):
    """One resolved duplicate group within a candidate cluster: the subset of
    member slugs that are truly the same entity, plus the fused canonical
    title + body. A cluster resolver returns a list of these (dropping members
    it judges distinct)."""
    members: list[str]
    title: str
    body: str


class MergeRecord(BaseModel):
    canonical: str
    absorbed: list[str] = Field(default_factory=list)
    new_settlement: str | None = None


class SettleReport(BaseModel):
    merged: list[MergeRecord] = Field(default_factory=list)
    promoted: list[str] = Field(default_factory=list)
