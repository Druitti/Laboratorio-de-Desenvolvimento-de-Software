import pytest

from lab04.null_dist import mannwhitney_null, split_groups, welch_null
from lab04.plots import GROUP_COLORS, TEST_COLORS, fig_g1, fig_g2, fig_g3, fig_g4
from lab04.robustness import run_robustness
from lab04.simulation import simulate_groups

REAL = {
    "com_bot": [4.0, 6.0, 8.0, 10.0, 13.0, 20.0],
    "sem_bot": [8.0, 12.0, 15.0, 20.0, 28.0, 60.0],
}


@pytest.fixture(scope="module")
def simulated():
    return simulate_groups(REAL, n_per_group=30, seed=42)


@pytest.fixture(scope="module")
def g2(simulated):
    _, a, b = split_groups(simulated)
    return fig_g2(welch_null(a, b), mannwhitney_null(a, b, n_perm=1000, seed=1))


def _axis_titles(fig):
    return [
        axis["title"]["text"]
        for key, axis in fig.to_dict()["layout"].items()
        if key.startswith(("xaxis", "yaxis")) and axis.get("title", {}).get("text")
    ]


def test_g1_has_title_axes_units_and_legend(simulated):
    fig = fig_g1(REAL, simulated)
    assert fig.layout.title.text.startswith("G1")
    titles = _axis_titles(fig)
    assert any("horas" in t for t in titles)
    assert any("%" in t for t in titles)
    legend_names = [t.name for t in fig.data if t.showlegend]
    assert sorted(legend_names) == sorted(REAL)
    assert len(fig.data) == 4  # 2 grupos x (real, simulado)


def test_g1_group_colors_are_consistent_between_panels(simulated):
    fig = fig_g1(REAL, simulated)
    by_group = {}
    for trace in fig.data:
        by_group.setdefault(trace.name, set()).add(trace.marker.line.color)
    assert all(len(colors) == 1 for colors in by_group.values())
    assert {c for colors in by_group.values() for c in colors} == set(GROUP_COLORS)
    assert not set(GROUP_COLORS) & set(TEST_COLORS.values())


@pytest.mark.parametrize("largest,end", [(60.0, 2), (100.0, 3), (5361.8, 4)])
def test_g1_keeps_every_value_inside_the_shared_log_bins(largest, end):
    # O maior valor não pode cair no fim exclusivo do último intervalo, mesmo sendo potência de dez.
    fig = fig_g1({"a": [0.5, largest], "b": [2.0, 3.0]}, {"a": [1.0, 2.0], "b": [4.0, 5.0]})
    assert {(t.xbins.start, t.xbins.end, t.xbins.size) for t in fig.data} == {(-1, end, (end + 1) / 15)}
    for trace in fig.data:
        assert trace.xbins.start <= min(trace.x)
        assert max(trace.x) < trace.xbins.end


def test_g1_labels_the_log_axis_in_hours(simulated):
    fig = fig_g1(REAL, simulated)
    assert "log" in fig.layout.xaxis.title.text
    assert fig.layout.xaxis.range == fig.layout.xaxis2.range
    assert list(fig.layout.xaxis.tickvals) == list(fig.layout.xaxis2.tickvals)
    labels = dict(zip(fig.layout.xaxis.tickvals, fig.layout.xaxis.ticktext))
    assert labels[1] == "10"
    assert labels[2] == "100"


def test_g1_rejects_mismatched_groups(simulated):
    with pytest.raises(ValueError, match="mesmos grupos"):
        fig_g1(REAL, {"a": [1.0], "b": [2.0]})


def test_g2_has_title_axes_units_and_legend(g2):
    assert g2.layout.title.text.startswith("G2")
    titles = _axis_titles(g2)
    assert any("adimensional" in t for t in titles)
    assert any("nº de pares" in t for t in titles)
    names = [t.name for t in g2.data if t.showlegend is not False]
    assert any("região de rejeição" in n for n in names)
    assert any("p-valor" in n for n in names)
    assert any("observado" in n for n in names)


def test_g2_uses_one_color_per_test(g2):
    welch = [t for t in g2.data if t.name and t.name.startswith("Welch")]
    mw = [t for t in g2.data if t.name and t.name.startswith("Mann-Whitney")]
    assert welch and mw
    for trace in welch:
        assert TEST_COLORS["Welch"] == _hex(trace)
    for trace in mw:
        assert TEST_COLORS["Mann-Whitney"] == _hex(trace)


def _hex(trace):
    color = trace.line.color if trace.type == "scatter" and trace.line.width != 0 else None
    if trace.type == "scatter" and trace.fillcolor:
        color = trace.fillcolor
    if trace.type == "bar":
        color = trace.marker.color
    if color.startswith("rgba"):
        r, g, b = (int(x) for x in color[5:-1].split(",")[:3])
        return f"#{r:02x}{g:02x}{b:02x}"
    return color


@pytest.fixture(scope="module")
def q3_report():
    return run_robustness(REAL, repetitions=200, seed=3, effects=(0, 0.5, 1.0))


def test_g3_has_one_bar_per_test_with_alpha_line_and_labels(q3_report):
    fig = fig_g3(q3_report)
    assert fig.layout.title.text.startswith("G3")
    assert {t.name: t.marker.color for t in fig.data} == TEST_COLORS
    for trace in fig.data:
        assert len(trace.x) == 2  # referência e outliers
        assert all(0 <= y <= 100 for y in trace.y)
    line = fig.layout.shapes[0]
    assert line.y0 == line.y1 == pytest.approx(5.0)
    assert "%" in fig.layout.yaxis.title.text and "Situação" in fig.layout.xaxis.title.text


def test_g3_values_come_from_the_report(q3_report):
    fig = fig_g3(q3_report)
    welch = next(t for t in fig.data if t.name == "Welch")
    ref = q3_report["scenarios"]["lognormal_reference"]["q1_type_i"]["welch"]
    assert welch.y[0] == pytest.approx(100 * ref)


def test_g4_has_both_tests_in_both_situations_with_test_colors(q3_report):
    fig = fig_g4(q3_report)
    assert fig.layout.title.text.startswith("G4")
    assert len(fig.data) == 4
    for trace in fig.data:
        test = trace.name.split(" — ")[0]
        assert trace.line.color == TEST_COLORS[test]
        assert list(trace.x) == [0.0, 0.5, 1.0]
    assert {t.line.dash for t in fig.data} == {"solid", "dash"}
    assert "log(horas)" in fig.layout.xaxis.title.text and "%" in fig.layout.yaxis.title.text
    assert fig.layout.shapes[0].y0 == pytest.approx(5.0)


def test_g3_g4_reject_incomplete_report():
    for build in (fig_g3, fig_g4):
        with pytest.raises(ValueError, match="incompletos"):
            build({"scenarios": {}})


def test_power_complement_has_both_tests_in_both_panels_with_consistent_colors():
    import json
    from pathlib import Path

    from lab04.plots import fig_power_complement

    report = json.loads((Path(__file__).resolve().parents[1] / "data" / "q1_q2.json").read_text(encoding="utf-8"))
    fig = fig_power_complement(report)
    assert fig.layout.title.text.startswith("Complemento de G4")
    assert len(fig.data) == 4
    assert {t.name for t in fig.data} == set(TEST_COLORS)
    for trace in fig.data:
        assert trace.line.color == TEST_COLORS[trace.name]
    titles = _axis_titles(fig)
    assert any("PRs por grupo" in t for t in titles)
    assert any("σ" in t for t in titles)
    assert any("%" in t for t in titles)


def test_power_complement_rejects_incomplete_results():
    from lab04.plots import fig_power_complement

    with pytest.raises(ValueError, match="Q1/Q2"):
        fig_power_complement({"observed_effect": {}})
