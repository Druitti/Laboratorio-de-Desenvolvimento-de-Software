import csv

import numpy as np
import pytest

from lab04.simulation import compare_groups, read_real_samples, simulate_groups


SAMPLES = {
    "with_review_bot": [4.0, 6.0, 8.0, 10.0, 13.0],
    "without_review_bot": [8.0, 12.0, 15.0, 20.0, 28.0],
}


def test_simulation_is_reproducible_and_keeps_requested_size():
    first = simulate_groups(SAMPLES, n_per_group=30, seed=123)
    second = simulate_groups(SAMPLES, n_per_group=30, seed=123)
    assert first.keys() == second.keys()
    for group in first:
        assert len(first[group]) == 30
        np.testing.assert_array_equal(first[group], second[group])
        assert np.isfinite(first[group]).all()
        assert (first[group] > 0).all()


def test_compare_runs_both_tests_on_the_two_groups():
    simulated = simulate_groups(SAMPLES, n_per_group=30, seed=10)
    result = compare_groups(simulated)
    assert result["groups"] == ["with_review_bot", "without_review_bot"]
    assert set(result["tests"]) == {"welch", "mann_whitney"}
    for test_result in result["tests"].values():
        assert 0 <= test_result["p_value"] <= 1
        assert test_result["interpretation"]
        assert test_result["null_hypothesis"]
        assert test_result["alternative_hypothesis"]


def test_reader_rejects_nonpositive_times(tmp_path):
    path = tmp_path / "real.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["group", "value"])
        writer.writerows([("A", 0), ("A", 2), ("B", 3), ("B", 4)])
    with pytest.raises(ValueError, match="positivo"):
        read_real_samples(path)


def test_reader_requires_two_groups_and_two_values_each(tmp_path):
    path = tmp_path / "real.csv"
    path.write_text("group,value\nA,1\nA,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exatamente dois grupos"):
        read_real_samples(path)

    path.write_text("group,value\nA,1\nB,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pelo menos duas"):
        read_real_samples(path)


@pytest.mark.parametrize("n,seed", [(1, 42), (30, -1)])
def test_simulation_rejects_invalid_configuration(n, seed):
    with pytest.raises(ValueError):
        simulate_groups(SAMPLES, n_per_group=n, seed=seed)
