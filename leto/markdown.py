from __future__ import annotations

import frontmatter

from leto.model import (
    Edge, ExperiencePayload, FactPayload, Kind, Note, ProcedurePayload, Settlement,
)

_PAYLOAD_FOR = {
    Kind.FACT: FactPayload,
    Kind.PROCEDURE: ProcedurePayload,
    Kind.EXPERIENCE: ExperiencePayload,
}


def _render_body(note: Note) -> str:
    """A human-readable view of the note. Not parsed back — frontmatter is
    canonical."""
    lines = [f"# {note.title}", ""]
    p = note.payload
    if note.kind is Kind.FACT:
        lines.append(p.definition)
    elif note.kind is Kind.PROCEDURE:
        lines.append(f"**Goal:** {p.goal}")
    else:  # experience
        lines += [
            f"**Situation:** {p.situation}", "",
            f"**Action:** {p.action}", "",
            f"**Outcome:** {p.outcome.value}", "",
            f"**Lesson:** {p.lesson}",
        ]
    return "\n".join(lines).strip()


def note_to_markdown(note: Note) -> str:
    post = frontmatter.Post(
        _render_body(note),
        kind=note.kind.value,
        title=note.title,
        settlement=note.settlement.value,
        sources=list(note.sources),
        aliases=list(note.aliases),
        valid_from=note.valid_from,
        valid_to=note.valid_to,
        recorded_at=note.recorded_at,
        promoted_from=list(note.promoted_from),
        payload=note.payload.model_dump(mode="json"),
        edges=[e.model_dump(mode="json") for e in note.edges],
    )
    return frontmatter.dumps(post)


def note_from_markdown(text: str, slug: str) -> Note:
    post = frontmatter.loads(text)
    kind = Kind(post["kind"])
    payload = _PAYLOAD_FOR[kind](**(post.get("payload") or {}))
    return Note(
        slug=slug,
        kind=kind,
        title=post["title"],
        settlement=Settlement(post.get("settlement", "fleeting")),
        sources=list(post.get("sources", []) or []),
        aliases=list(post.get("aliases", []) or []),
        valid_from=post.get("valid_from"),
        valid_to=post.get("valid_to"),
        recorded_at=post.get("recorded_at"),
        promoted_from=list(post.get("promoted_from", []) or []),
        edges=[Edge(**e) for e in (post.get("edges", []) or [])],
        payload=payload,
    )
