import math

import numpy as np
import pytest

from lab05.pilot import ROOT
from lab05.power import (
    DESIGN_METRICS,
    DESIGN_RATIO,
    METRICS,
    choose_n,
    fit_group,
    load_conditions,
    normal_approximation_n,
    pooled_contamination,
    run_power,
    sigma_upper_factor,
    time_budget,
)

DATA = ROOT / "lab05" / "data"
SMALL = {
    "repetitions": 300,
    "sample_sizes": (5, 40),
    "ratios": (1.0, DESIGN_RATIO, 1.5),
    "metrics": ("write_throughput",),
    "scenarios": ("lognormal", "contaminada", "sigma_superior"),
}


@pytest.fixture(scope="module")
def conditions():
    return load_conditions(DATA / "pilot.csv", DATA / "validation.csv")


@pytest.fixture(scope="module")
def report(conditions):
    return run_power(conditions, seed=3, **SMALL)


def test_load_conditions_has_ten_runs_per_mode_for_every_metric(conditions):
    assert set(conditions) == set(METRICS)
    assert all(len(values) == 10 for metric in conditions.values() for values in metric.values())


def test_fit_group_flags_a_slow_outlier():
    fit = fit_group([100, 101, 99, 100, 102, 98, 100, 101, 99, 70])
    assert fit["outlier_probability"] == pytest.approx(0.1)
    assert fit["outlier_log_shift"] < -0.2
    assert fit["robust_sigma_log"] < fit["sd_log"]


def test_fit_group_without_outliers_has_no_contamination():
    fit = fit_group([100, 101, 99, 100, 102, 98, 100, 101])
    assert fit["outlier_probability"] == 0.0 and fit["outlier_log_shift"] == 0.0


def test_fit_group_rejects_short_or_non_positive_samples():
    with pytest.raises(ValueError):
        fit_group([1, 2, 3])
    with pytest.raises(ValueError):
        fit_group([1, 2, 3, 0])


def test_sigma_upper_factor_matches_chi_square_bound():
    assert sigma_upper_factor(10) == pytest.approx(1.64, abs=0.01)
    assert sigma_upper_factor(100) < sigma_upper_factor(10)


def test_pooled_contamination_is_symmetric_in_the_modes(conditions):
    fits = {mode: fit_group(conditions["write_throughput"][mode]) for mode in ("delete", "wal")}
    swapped = {"delete": fits["wal"], "wal": fits["delete"]}
    assert pooled_contamination(fits) == pytest.approx(pooled_contamination(swapped))


def test_report_structure_and_type_i_near_alpha(report):
    scenarios = report["metrics"]["write_throughput"]["scenarios"]
    assert set(scenarios) == {"lognormal", "contaminada", "sigma_superior"}
    for scenario in scenarios.values():
        assert len(scenario["rows"]) == 6
        null_rows = [row for row in scenario["rows"] if row["ratio"] == 1.0 and row["n_per_group"] == 40]
        for rate in null_rows[0]["rejection_proportion"].values():
            assert rate < 0.08


def test_power_grows_with_n_and_with_effect(report):
    rows = report["metrics"]["write_throughput"]["scenarios"]["contaminada"]["rows"]
    power = {(r["n_per_group"], r["ratio"]): r["rejection_proportion"]["mann_whitney"] for r in rows}
    assert power[(40, 1.5)] >= power[(5, 1.5)]
    assert power[(40, 1.5)] > power[(40, DESIGN_RATIO)] >= power[(40, 1.0)] - 0.03
    assert power[(40, 1.5)] > 0.9


def test_observed_effect_is_the_pilot_ratio(conditions, report):
    ratio = report["metrics"]["write_throughput"]["observed_ratio_wal_over_delete"]
    expected = np.exp(np.mean(np.log(conditions["write_throughput"]["wal"])) - np.mean(np.log(conditions["write_throughput"]["delete"])))
    assert ratio == pytest.approx(expected)
    assert ratio > 4


def test_normal_approximation_follows_the_closed_form():
    fits = {"delete": {"sd_log": 0.1}, "wal": {"sd_log": 0.1}}
    z = 2.2414 + 0.8416
    assert normal_approximation_n(fits, ratio=1.05, alpha=0.025) == math.ceil(0.02 * z**2 / math.log(1.05) ** 2)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"repetitions": 10},
        {"sample_sizes": (10, 5)},
        {"sample_sizes": (1, 5)},
        {"ratios": (1.05, 1.1)},
        {"ratios": (1.0, 1.1)},
        {"alpha": 0.0},
        {"seed": -1},
        {"metrics": ("inexistente",)},
        {"scenarios": ("inexistente",)},
    ],
)
def test_run_power_validates_parameters(conditions, kwargs):
    options = {**SMALL, **kwargs}
    with pytest.raises(ValueError):
        run_power(conditions, **options)


def _fake_report(needed: dict) -> dict:
    return {"metrics": {key: {"scenarios": {"contaminada": {"n_for_target_power": value}}} for key, value in needed.items()}}


def test_choose_n_takes_the_largest_case_and_adds_warmup():
    decision = choose_n(_fake_report({
        "write_throughput": {"welch": 60, "mann_whitney": 80},
        "read_throughput": {"welch": 100, "mann_whitney": 15},
        "read_single_transaction": {"welch": None, "mann_whitney": 60},
    }))
    assert decision["analysis_n"] == 100
    assert decision["planned_runs"] == 102
    assert decision["binding"] == "read_throughput/contaminada"
    assert decision["uses_robust_test_only"] == ["read_single_transaction/contaminada"]


def test_choose_n_reports_when_the_grid_is_too_small():
    decision = choose_n(_fake_report({key: {"welch": None, "mann_whitney": None} for key in DESIGN_METRICS}))
    assert decision["analysis_n"] is None and "ampliar a grade" in decision["note"]


def test_time_budget_scales_with_planned_runs(conditions):
    one, ten = time_budget(conditions, 1), time_budget(conditions, 10)
    assert ten["total_seconds"] == pytest.approx(10 * one["total_seconds"])
    assert {item["metric"] for item in one["items"]} == {k for k, v in METRICS.items() if v["operations"]}
