import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "nell", Path(__file__).with_name("nell.py"))
nell = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nell)


def test_hash_embedder_is_deterministic_and_shaped():
    v1 = nell._hash_embedder("Alan Turing computer science")
    v2 = nell._hash_embedder("Alan Turing computer science")
    assert v1 == v2
    assert len(v1) == 256
    # shared tokens => nonzero overlap; disjoint text => different vector
    assert nell._hash_embedder("water liquid") != v1
    assert sum(v1) > 0
