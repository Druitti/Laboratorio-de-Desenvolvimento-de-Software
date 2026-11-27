import matplotlib
import pytest

matplotlib.use("Agg")

from lab05.pilot import ROOT
from lab05.plots import FIGURES, fig_f1, fig_f2, fig_f3, fig_f4, fig_f5, read_pilot
from lab05.power import DESIGN_METRICS, load_conditions, run_power

DATA = ROOT / "lab05" / "data"


@pytest.fixture(scope="module")
def inputs():
    rows = read_pilot(DATA / "pilot.csv")
    conditions = load_conditions(DATA / "pilot.csv", DATA / "validation.csv")
    report = run_power(
        conditions, repetitions=200, sample_sizes=(5, 20), ratios=(1.0, 1.05), seed=1,
        metrics=DESIGN_METRICS, scenarios=("contaminada",),
    )
    return rows, conditions, report


def test_every_figure_renders_and_saves(inputs, tmp_path):
    rows, conditions, report = inputs
    figures = [fig_f1(rows), fig_f2(rows), fig_f3(conditions), fig_f4(report), fig_f5(rows)]
    assert len(figures) == len(FIGURES)
    for index, fig in enumerate(figures):
        target = tmp_path / f"{index}.png"
        fig.savefig(target, dpi=40)
        assert target.stat().st_size > 1000
