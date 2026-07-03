"""LETO — Learning Engine Through Ontologies (engine core)."""

from leto.consolidate import (
    Consolidator, Embedder, Gate, Merger, rerank,
)
from leto.engine import Engine, Extractor
from leto.model import (
    ExtractedItem, KnowledgeBlob, MergedGroup, MergeRecord, Note, NoteKind,
    RecalledNote, Settlement, SettleReport, slugify,
)
from leto.store import NoteStore

__version__ = "0.0.1"

__all__ = [
    "Engine", "Extractor", "NoteStore", "Consolidator",
    "Embedder", "Merger", "Gate", "rerank",
    "Note", "NoteKind", "Settlement", "ExtractedItem",
    "RecalledNote", "KnowledgeBlob", "MergedGroup", "MergeRecord",
    "SettleReport", "slugify", "__version__",
]
