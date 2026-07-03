from leto.consolidate import rerank


def test_rerank_ranks_item_present_in_both_lists_first():
    vector = ["a", "b", "c"]
    keyword = ["b", "d", "a"]
    fused = rerank(vector, keyword)
    # 'a' (ranks 0 and 2) and 'b' (ranks 1 and 0) beat singletons c, d
    assert set(fused[:2]) == {"a", "b"}
    assert "c" in fused and "d" in fused


def test_rerank_empty_inputs_return_empty():
    assert rerank([], []) == []
