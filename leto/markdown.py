from __future__ import annotations

import frontmatter

from leto.model import Note, NoteKind, Settlement


def note_to_markdown(note: Note) -> str:
    post = frontmatter.Post(
        note.body,
        kind=note.kind.value,
        title=note.title,
        settlement=note.settlement.value,
        links=list(note.links),
        sources=list(note.sources),
        aliases=list(note.aliases),
    )
    return frontmatter.dumps(post)


def note_from_markdown(text: str, slug: str) -> Note:
    post = frontmatter.loads(text)
    return Note(
        slug=slug,
        kind=NoteKind(post["kind"]),
        title=post["title"],
        body=post.content,
        settlement=Settlement(post.get("settlement", "fleeting")),
        links=list(post.get("links", []) or []),
        sources=list(post.get("sources", []) or []),
        aliases=list(post.get("aliases", []) or []),
    )
