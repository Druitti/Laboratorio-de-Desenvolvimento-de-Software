import numpy as np
import pytest
from scipy import stats

from lab04.robustness import _rejection_rates, run_robustness


REAL = {
    "with_review_bot": [10, 15, 25, 40, 70, 110, 200, 500],
    "without_review_bot": [5, 12, 22, 35, 80, 140, 300, 800],
}


def test_q3_repeats_q1_and_q2_in_reference_and_outlier_scenarios():
    result = run_robustness(REAL, repetitions=200, seed=7, effects=(0, 0.5, 1.0))
    assert set(result["scenarios"]) == {"lognormal_reference", "outlier_contamination"}
    for scenario in result["scenarios"].values():
        assert set(scenario["q1_type_i"]) == {"welch", "mann_whitney"}
        assert len(scenario["q2"]) == 3
        assert scenario["q2"][0]["effect_log_shift"] == 0
        assert scenario["q2"][0]["rejection_proportion"] == scenario["q1_type_i"]


def test_q3_is_reproducible_for_a_fixed_seed():
    kwargs = {"repetitions": 200, "seed": 91, "effects": (0, 0.25, 0.5)}
    first = run_robustness(REAL, **kwargs)
    second = run_robustness(REAL, **kwargs)
    assert first == second


def test_vectorized_test_rates_match_scipy_for_one_generated_replication():
    rng = np.random.default_rng(12)
    a = rng.lognormal(2, 1.4, size=(1, 30))
    b = rng.lognormal(2.2, 1.4, size=(1, 30))
    rates = _rejection_rates(a, b, alpha=0.05)
    welch = stats.ttest_ind(a[0], b[0], equal_var=False).pvalue < 0.05
    mann_whitney = stats.mannwhitneyu(a[0], b[0], alternative="two-sided", method="asymptotic").pvalue < 0.05
    assert rates["welch"] == float(welch)
    assert rates["mann_whitney"] == float(mann_whitney)


@pytest.mark.parametrize("kwargs", [
    {"repetitions": 99},
    {"n_per_group": 1},
    {"alpha": 1.0},
    {"seed": -1},
    {"effects": (0.1, 0.2)},
    {"outlier_probability": 1.1},
    {"outlier_multiplier": 1},
])
def test_q3_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        run_robustness(REAL, **kwargs)
