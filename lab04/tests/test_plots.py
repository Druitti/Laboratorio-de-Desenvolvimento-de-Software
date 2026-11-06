import pytest

from lab04.null_dist import mannwhitney_null, split_groups, welch_null
from lab04.plots import GROUP_COLORS, TEST_COLORS, fig_g1, fig_g2
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
