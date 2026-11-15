import numpy as np

from foodswap.search import rrf, top


def test_top_keeps_only_eligible_products_best_first():
    scores = np.array([0.9, 0.1, 0.8, 0.5])
    mask = np.array([False, True, True, True])
    assert top(scores, mask, 2).tolist() == [2, 3]


def test_top_can_require_a_positive_score():
    scores = np.array([0.0, 2.0, 0.0])
    assert top(scores, np.ones(3, bool), 3, positive_only=True).tolist() == [1]


def test_top_with_nothing_eligible_is_empty():
    assert top(np.array([1.0, 2.0]), np.zeros(2, bool), 5).tolist() == []


def test_rrf_rewards_products_both_lists_agree_on():
    keyword = [1, 2, 3]
    dense = [3, 1, 4]
    fused = [i for i, _ in rrf([keyword, dense], k=60)]
    assert fused[:2] == [1, 3]  # in both lists near the top
    assert set(fused) == {1, 2, 3, 4}


def test_rrf_score_is_sum_of_reciprocal_ranks():
    fused = dict(rrf([[7], [5, 7]], k=60))
    assert np.isclose(fused[7], 1 / 61 + 1 / 62)
    assert np.isclose(fused[5], 1 / 61)
