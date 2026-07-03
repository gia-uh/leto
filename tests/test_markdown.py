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


def test_roundtrip_preserves_sources_and_aliases():
    from leto.model import Note, NoteKind, Settlement
    from leto.markdown import note_to_markdown, note_from_markdown
    note = Note(
        slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing",
        body="A mathematician.", settlement=Settlement.DEVELOPING,
        links=["computer-science"],
        sources=["https://a", "https://b"],
        aliases=["turing-alan"],
    )
    back = note_from_markdown(note_to_markdown(note), slug="alan-turing")
    assert back == note


def test_missing_sources_and_aliases_default_to_empty():
    from leto.markdown import note_from_markdown
    text = "---\nkind: entity\ntitle: Water\nsettlement: fleeting\nlinks: []\n---\nH2O."
    note = note_from_markdown(text, slug="water")
    assert note.sources == []
    assert note.aliases == []
