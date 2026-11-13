import json
import math

import numpy as np
import pytest

from lab04.power import main, observed_log_shift, run_power, smallest_n_reaching

REAL = {
    "with_review_bot": [10, 15, 25, 40, 70, 110, 200, 500],
    "without_review_bot": [5, 12, 22, 35, 80, 140, 300, 800],
}
SMALL = {"repetitions": 300, "sample_sizes": (5, 20), "effects": (0, 1.0), "sigmas": (0.5,), "skew_n": 10}


@pytest.fixture(scope="module")
def report():
    return run_power(REAL, seed=3, **SMALL)


def test_q1_rows_are_the_zero_effect_rows_of_q2(report):
    assert [row["n_per_group"] for row in report["q1_type_i"]] == [5, 20]
    assert len(report["q2_power"]) == 4
    zero = [row["rejection_proportion"] for row in report["q2_power"] if row["effect_log_shift"] == 0]
    assert [row["rejection_proportion"] for row in report["q1_type_i"]] == zero
    for row in report["q2_power"]:
        assert set(row["rejection_proportion"]) == {"welch", "mann_whitney"}
        assert row["median_ratio"] == pytest.approx(math.exp(row["effect_log_shift"]))


def test_observed_effect_uses_the_difference_of_log_means(report):
    logs = {g: np.log(v) for g, v in REAL.items()}
    expected = abs(logs["with_review_bot"].mean() - logs["without_review_bot"].mean())
    assert observed_log_shift(REAL) == pytest.approx(expected)
    assert report["observed_effect"]["log_shift"] == pytest.approx(expected)
    assert len(report["observed_effect"]["power"]) == 2


def test_skew_grid_marks_the_real_fit(report):
    rows = report["skewness_sensitivity"]["rows"]
    assert sum(row["is_real_fit"] for row in rows) == 1
    real = next(row for row in rows if row["is_real_fit"])
    assert real["sigma_log_hours"] == report["real_data_fit"]["sigma_log_hours"]


def test_results_are_reproducible_for_a_fixed_seed(report):
    assert run_power(REAL, seed=3, **SMALL) == report
    assert run_power(REAL, seed=4, **SMALL) != report


def test_power_grows_with_sample_size_for_a_large_effect():
    result = run_power(REAL, repetitions=800, sample_sizes=(5, 60), effects=(0, 2.0), sigmas=(0.5,), seed=1)
    power = {row["n_per_group"]: row["rejection_proportion"] for row in result["q2_power"] if row["effect_log_shift"]}
    assert power[60]["mann_whitney"] > power[5]["mann_whitney"] + 0.3


def test_welch_is_calibrated_when_data_are_almost_normal_and_conservative_with_heavy_tails():
    result = run_power(REAL, repetitions=4000, sample_sizes=(10,), effects=(0,), sigmas=(0.1, 2.5), skew_n=30, seed=5)
    rows = {round(row["sigma_log_hours"], 2): row for row in result["skewness_sensitivity"]["rows"]}
    assert 0.035 < rows[0.1]["type_i"]["welch"] < 0.065
    assert rows[2.5]["type_i"]["welch"] < 0.035
    assert 0.035 < rows[2.5]["type_i"]["mann_whitney"] < 0.065


def test_smallest_n_reaching_the_target():
    rows = [{"n_per_group": n, "rejection_proportion": {"welch": p, "mann_whitney": p}} for n, p in
            ((10, 0.3), (30, 0.81), (60, 0.95))]
    assert smallest_n_reaching(rows, "welch") == 30
    assert smallest_n_reaching(rows[:1], "welch") is None


@pytest.mark.parametrize("kwargs", [
    {"repetitions": 99},
    {"sample_sizes": (20, 10)},
    {"sample_sizes": (1, 10)},
    {"effects": (0.2, 0.4)},
    {"sigmas": (0,)},
    {"alpha": 0},
    {"seed": -1},
])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        run_power(REAL, **{**SMALL, **kwargs})


def test_cli_writes_json_and_markdown(tmp_path):
    csv = tmp_path / "real.csv"
    csv.write_text("group,value\n" + "".join(f"{g},{v}\n" for g, vs in REAL.items() for v in vs), encoding="utf-8")
    output, report = tmp_path / "q1_q2.json", tmp_path / "q1-q2.md"
    assert main(["--input", str(csv), "--output", str(output), "--report", str(report),
                 "--repetitions", "200", "--sample-sizes", "5", "10"]) == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["sample_sizes"] == [5, 10]
    text = report.read_text(encoding="utf-8")
    assert "## Q1" in text and "## Q2" in text and "efeito observado" in text
