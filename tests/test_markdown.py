from leto.model import Note, NoteKind, Settlement
from leto.markdown import note_to_markdown, note_from_markdown


def test_roundtrip_preserves_all_fields():
    note = Note(
        slug="alan-turing",
        kind=NoteKind.ENTITY,
        title="Alan Turing",
        body="A mathematician who founded computer science.",
        settlement=Settlement.FLEETING,
        links=["computer-science", "enigma"],
    )
    text = note_to_markdown(note)
    assert text.startswith("---")
    back = note_from_markdown(text, slug="alan-turing")
    assert back == note


def test_frontmatter_uses_enum_values_not_repr():
    note = Note(slug="x", kind=NoteKind.PROCEDURE, title="X")
    text = note_to_markdown(note)
    assert "kind: procedure" in text
    assert "settlement: fleeting" in text
