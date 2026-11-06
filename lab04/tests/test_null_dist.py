import numpy as np
import pytest
from scipy import stats
from scipy.integrate import trapezoid

from lab04.null_dist import mannwhitney_null, split_groups, welch_df, welch_null
from lab04.simulation import compare_groups, simulate_groups

REAL = {
    "com_bot": [4.0, 6.0, 8.0, 10.0, 13.0, 20.0],
    "sem_bot": [8.0, 12.0, 15.0, 20.0, 28.0, 60.0],
}


def _groups():
    simulated = simulate_groups(REAL, n_per_group=30, seed=42)
    _, first, second = split_groups(simulated)
    return simulated, first, second


def test_welch_df_matches_scipy_and_textbook_equal_case():
    _, a, b = _groups()
    result = stats.ttest_ind(a, b, equal_var=False)
    assert welch_df(a, b) == pytest.approx(result.df)
    # variâncias e n iguais: gl = 2(n-1)
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert welch_df(x, x + 10) == pytest.approx(6.0)


def test_welch_null_matches_compare_groups():
    simulated, a, b = _groups()
    result = compare_groups(simulated)["tests"]["welch"]
    null = welch_null(a, b)
    assert null.t_obs == pytest.approx(result["statistic"])
    assert null.p_value == pytest.approx(result["p_value"])
    assert null.critical == pytest.approx(stats.t(null.df).ppf(0.975))
    assert trapezoid(null.density, null.x) == pytest.approx(1.0, abs=0.01)


def test_mannwhitney_null_matches_scipy_statistic_and_p_value():
    simulated, a, b = _groups()
    result = compare_groups(simulated)["tests"]["mann_whitney"]
    null = mannwhitney_null(a, b, n_perm=10_000, seed=42)
    assert null.u_obs == pytest.approx(result["statistic"])
    assert null.p_value == pytest.approx(result["p_value"], abs=0.02)
    assert null.mean == pytest.approx(30 * 30 / 2)
    assert null.critical_low < null.mean < null.critical_high


def test_mannwhitney_null_is_reproducible_and_seed_dependent():
    _, a, b = _groups()
    first = mannwhitney_null(a, b, n_perm=500, seed=7)
    again = mannwhitney_null(a, b, n_perm=500, seed=7)
    other = mannwhitney_null(a, b, n_perm=500, seed=8)
    np.testing.assert_array_equal(first.u_null, again.u_null)
    assert not np.array_equal(first.u_null, other.u_null)


def test_invalid_arguments():
    _, a, b = _groups()
    with pytest.raises(ValueError, match="alpha"):
        welch_null(a, b, alpha=1.5)
    with pytest.raises(ValueError, match="n_perm"):
        mannwhitney_null(a, b, n_perm=10)
    with pytest.raises(ValueError, match="exatamente dois"):
        split_groups({"a": [1.0, 2.0]})
