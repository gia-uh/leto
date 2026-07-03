import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "nell", Path(__file__).with_name("nell.py"))
nell = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nell)


async def test_hash_embedder_is_deterministic_and_shaped():
    v1 = await nell._hash_embedder("Alan Turing computer science")
    v2 = await nell._hash_embedder("Alan Turing computer science")
    assert v1 == v2
    assert len(v1) == 256
    # shared tokens => nonzero overlap; disjoint text => different vector
    assert await nell._hash_embedder("water liquid") != v1
    assert sum(v1) > 0


def test_format_cycle_report_counts_by_settlement():
    from leto import Note, NoteKind, Settlement, SettleReport, MergeRecord
    notes = [
        Note(slug="a", kind=NoteKind.ENTITY, title="A", settlement=Settlement.FLEETING),
        Note(slug="b", kind=NoteKind.ENTITY, title="B", settlement=Settlement.DEVELOPING),
        Note(slug="c", kind=NoteKind.ENTITY, title="C", settlement=Settlement.DEVELOPING),
    ]
    report = SettleReport(merged=[MergeRecord(canonical="a", absorbed=["z"])],
                          promoted=["b", "c"])
    line = nell.format_cycle_report(3, notes, report)
    assert "cycle 3" in line
    assert "3 notes" in line
    assert "fleeting 1" in line
    assert "developing 2" in line
    assert "merged 1" in line
    assert "promoted 2" in line
