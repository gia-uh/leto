from leto.model import (
    NoteKind, Settlement, Note, ExtractedItem, KnowledgeBlob, slugify,
)


def test_slugify_kebab_cases_and_strips():
    assert slugify("  Alan Turing!  ") == "alan-turing"
    assert slugify("Café / Bar 42") == "caf-bar-42"


def test_note_defaults_to_fleeting_with_no_links():
    n = Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing")
    assert n.settlement is Settlement.FLEETING
    assert n.links == []
    assert n.body == ""


def test_extracted_item_roundtrips_fields():
    item = ExtractedItem(kind=NoteKind.PROCEDURE, title="Boil water",
                         body="Heat until 100C", links=["Water"])
    assert item.kind is NoteKind.PROCEDURE
    assert item.links == ["Water"]


def test_knowledge_blob_starts_empty():
    blob = KnowledgeBlob(query="who is turing")
    assert blob.facts == [] and blob.procedures == []


def test_note_has_empty_sources_and_aliases_by_default():
    from leto.model import Note, NoteKind
    n = Note(slug="alan-turing", kind=NoteKind.ENTITY, title="Alan Turing")
    assert n.sources == []
    assert n.aliases == []


def test_merge_and_report_types_construct():
    from leto.model import MergedGroup, MergeRecord, SettleReport
    m = MergedGroup(members=["alan-turing", "turing-alan"],
                    title="Alan Turing", body="A mathematician.")
    assert m.title == "Alan Turing"
    assert m.members == ["alan-turing", "turing-alan"]
    rec = MergeRecord(canonical="alan-turing", absorbed=["turing-alan"],
                      new_settlement="fleeting")
    report = SettleReport(merged=[rec], promoted=["alan-turing"])
    assert report.merged[0].absorbed == ["turing-alan"]
    assert report.promoted == ["alan-turing"]
    empty = SettleReport()
    assert empty.merged == [] and empty.promoted == []
