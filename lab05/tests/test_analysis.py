import math

import numpy as np
import pytest

from lab05.analysis import compare, geometric_ratio_ci, hedges_g, holm, probability_of_superiority


@pytest.fixture
def samples():
    rng = np.random.default_rng(1)
    return rng.lognormal(math.log(200), 0.05, 30), rng.lognormal(math.log(100), 0.05, 30)


def test_ratio_ci_covers_the_true_ratio(samples):
    wal, delete = samples
    ratio, low, high = geometric_ratio_ci(wal, delete, repetitions=2000)
    assert low < 2.0 < high
    assert low < ratio < high


def test_ratio_is_exact_for_constant_groups():
    ratio, low, high = geometric_ratio_ci([200, 200, 200], [100, 100, 100], repetitions=200)
    assert ratio == low == high == pytest.approx(2.0)


def test_hedges_g_sign_and_symmetry(samples):
    wal, delete = samples
    assert hedges_g(wal, delete) > 5
    assert hedges_g(wal, delete) == pytest.approx(-hedges_g(delete, wal))
    assert hedges_g([1, 2, 3], [1, 2, 3]) == 0.0


def test_probability_of_superiority_counts_ties_as_half():
    assert probability_of_superiority([3, 4], [1, 2]) == 1.0
    assert probability_of_superiority([1, 2], [3, 4]) == 0.0
    assert probability_of_superiority([1, 2], [1, 2]) == pytest.approx(0.5)


def test_compare_reports_both_tests_and_effect_sizes(samples):
    wal, delete = samples
    result = compare(wal, delete)
    assert result["welch_p"] < 1e-6 and result["mann_whitney_p"] < 1e-6
    assert result["geometric_ratio"] == pytest.approx(2.0, rel=0.05)
    assert result["probability_of_superiority"] == 1.0
    assert set(result["shapiro_p_log"]) == {"wal", "delete"}


def test_compare_rejects_invalid_values():
    with pytest.raises(ValueError):
        compare([1, 2, 0], [1, 2, 3])
    with pytest.raises(ValueError):
        compare([1], [1, 2])


def test_holm_adjusts_in_step_down_order():
    result = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert result["a"]["p_adjusted"] == pytest.approx(0.03)
    assert result["c"]["p_adjusted"] == pytest.approx(0.06)
    assert result["b"]["p_adjusted"] == pytest.approx(0.06)
    assert [result[k]["reject"] for k in "abc"] == [True, False, False]
    assert holm({"x": 0.5, "y": 0.9})["y"]["p_adjusted"] == pytest.approx(1.0)
