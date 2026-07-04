from leto.model import (
    Kind, Settlement, Outcome, Edge, EdgeType, Note,
    FactPayload, ProcedurePayload, ExperiencePayload,
)
from leto.markdown import note_to_markdown, note_from_markdown


def test_fact_roundtrips_via_frontmatter():
    note = Note(
        slug="alan-turing", kind=Kind.FACT, title="Alan Turing",
        settlement=Settlement.DEVELOPING, sources=["https://a", "https://b"],
        aliases=["turing-alan"], valid_from="2019-01-01", recorded_at="2026-07-04",
        edges=[Edge(target="computer-science", type=EdgeType.RELATES_TO)],
        payload=FactPayload(definition="A mathematician who founded CS."))
    back = note_from_markdown(note_to_markdown(note), slug="alan-turing")
    assert back == note


def test_experience_roundtrips_with_ordered_steps():
    note = Note(
        slug="break-enigma", kind=Kind.EXPERIENCE, title="Breaking Enigma",
        edges=[],
        payload=ExperiencePayload(situation="ciphertext only", action="crib attack",
                                  outcome=Outcome.WORKED, lesson="cribs help"))
    back = note_from_markdown(note_to_markdown(note), slug="break-enigma")
    assert back == note


def test_body_is_human_readable_view():
    note = Note(slug="do-x", kind=Kind.PROCEDURE, title="Do X",
                payload=ProcedurePayload(goal="accomplish x"))
    text = note_to_markdown(note)
    assert text.startswith("---")
    assert "# Do X" in text
    assert "accomplish x" in text
