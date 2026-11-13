"""Gráficos do dashboard do Lab04 (G1 a G4).

Convenção de cores: cada *teste* tem uma cor fixa (``TEST_COLORS``) usada em
todos os gráficos; os *grupos* de dados (G1) usam uma paleta diferente para não
serem confundidos com os testes.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lab04.null_dist import MannWhitneyNull, WelchNull

TEST_COLORS = {"Welch": "#2a78d6", "Mann-Whitney": "#eb6834"}
GROUP_COLORS = ("#1b9e77", "#7b4fa3")
OBSERVED_COLOR = "#0b0b0b"
BACKGROUND = "#fcfcfb"
TEXT = "#0b0b0b"
GRID = "#e1e0d9"


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def _style(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.01),
        height=height,
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,
        font=dict(color=TEXT, size=13),
        legend=dict(orientation="h", yanchor="top", y=-0.22, x=0),
        margin=dict(l=60, r=20, t=70, b=40),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def fig_g1(
    real: Mapping[str, Iterable[float]],
    simulated: Mapping[str, Iterable[float]],
    *,
    n_bins: int = 15,
) -> go.Figure:
    """G1: histograma de cada grupo, dados reais (esquerda) × simulados (direita).

    Os dois painéis usam os mesmos intervalos (bins) e o eixo y em porcentagem
    do grupo, para que tamanhos de amostra diferentes não distorçam a comparação.
    Os intervalos são iguais em escala logarítmica: em escala linear, a cauda dos
    tempos de merge deixa quase todos os PRs no primeiro intervalo.
    """
    groups = sorted(real)
    if sorted(simulated) != groups:
        raise ValueError("Dados reais e simulados devem ter os mesmos grupos.")
    colors = dict(zip(groups, GROUP_COLORS))
    log_hours = [{g: np.log10(np.asarray(list(s[g]), dtype=float)) for g in groups} for s in (real, simulated)]
    values = np.concatenate([panel[g] for panel in log_hours for g in groups])
    # floor + 1 mantém o maior valor dentro do último intervalo, cujo fim é exclusivo.
    low, high = int(np.floor(values.min())), int(np.floor(values.max())) + 1
    bins = dict(start=low, end=high, size=(high - low) / n_bins)

    n_real = {g: len(list(real[g])) for g in groups}
    n_sim = {g: len(list(simulated[g])) for g in groups}
    fig = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        horizontal_spacing=0.04,
        subplot_titles=(
            "Dados reais (n = " + " / ".join(str(n_real[g]) for g in groups) + ")",
            "Dados simulados (n = " + " / ".join(str(n_sim[g]) for g in groups) + ")",
        ),
    )
    for col, data in enumerate(log_hours, start=1):
        for group in groups:
            fig.add_trace(
                go.Histogram(
                    x=list(data[group]),
                    xbins=bins,
                    histnorm="percent",
                    name=group,
                    legendgroup=group,
                    showlegend=col == 1,
                    hovertemplate="%{y:.1f}% dos PRs do grupo<extra>%{fullData.name}</extra>",
                    marker=dict(color=_rgba(colors[group], 0.6), line=dict(color=colors[group], width=1)),
                ),
                row=1,
                col=col,
            )
    fig.update_layout(barmode="overlay")
    ticks = list(range(low, high + 1))
    fig.update_xaxes(
        title_text="Tempo até o merge (horas, escala log)",
        range=[low, high],
        tickvals=ticks,
        ticktext=[f"{10.0**tick:g}" for tick in ticks],
    )
    fig.update_yaxes(title_text="% dos PRs do grupo", col=1)
    return _style(fig, "G1 — Tempo até o merge: dados reais × dados simulados", 440)


def fig_g2(
    welch: WelchNull,
    mw: MannWhitneyNull,
    *,
    alpha: float = 0.05,
    bins: int = 50,
) -> go.Figure:
    """G2: estatística de cada teste sob H0, rejeição e p-valor do exemplo sombreados."""
    fig = make_subplots(
        rows=1,
        cols=2,
        horizontal_spacing=0.10,
        subplot_titles=("t de Welch sob H0", "U de Mann–Whitney sob H0 (permutação)"),
    )
    _welch_panel(fig, welch, alpha)
    _mannwhitney_panel(fig, mw, alpha, bins)
    fig.update_xaxes(title_text="Estatística t (adimensional)", col=1)
    fig.update_yaxes(title_text="Densidade (1/unid. de t)", col=1)
    fig.update_xaxes(title_text="U de Mann–Whitney (nº de pares)", col=2)
    fig.update_yaxes(title_text="Densidade (1/unid. de U)", col=2)
    return _style(fig, f"G2 — Distribuição da estatística sob H0 (α = {alpha:.0%}, bilateral)", 520)


def _welch_panel(fig: go.Figure, null: WelchNull, alpha: float) -> None:
    color = TEST_COLORS["Welch"]
    x, y = null.x, null.density
    fig.add_trace(
        go.Scatter(x=x, y=y, mode="lines", name="Welch: t sob H0", line=dict(color=color, width=2)),
        row=1,
        col=1,
    )
    reject = (x <= -null.critical, x >= null.critical)
    pval = (x <= -abs(null.t_obs), x >= abs(null.t_obs))
    _shade(fig, x, y, reject, f"Welch: região de rejeição (α = {alpha:.0%})", _rgba(color, 0.30), 1, None)
    _shade(
        fig, x, y, pval, f"Welch: área do p-valor (p = {null.p_value:.3f})", _rgba(color, 0.95), 1, None
    )
    _observed(fig, null.t_obs, float(y.max()), f"t observado = {null.t_obs:.2f}", 1)


def _shade(fig, x, y, masks, name, fill, col, pattern):
    for i, mask in enumerate(masks):
        if mask.sum() < 2:
            continue
        kwargs = dict(fillpattern=dict(shape=pattern, fgcolor=fill, bgcolor="rgba(0,0,0,0)")) if pattern else {}
        fig.add_trace(
            go.Scatter(
                x=x[mask],
                y=y[mask],
                mode="lines",
                line=dict(width=0, color=fill),
                fill="tozeroy",
                fillcolor=fill,
                name=name,
                legendgroup=name,
                showlegend=i == 0,
                hoverinfo="skip",
                **kwargs,
            ),
            row=1,
            col=col,
        )


def _mannwhitney_panel(fig: go.Figure, null: MannWhitneyNull, alpha: float, bins: int) -> None:
    color = TEST_COLORS["Mann-Whitney"]
    low = min(float(null.u_null.min()), null.u_obs)
    high = max(float(null.u_null.max()), null.u_obs)
    density, edges = np.histogram(null.u_null, bins=bins, range=(low, high), density=True)
    centers = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]
    reject = (centers <= null.critical_low) | (centers >= null.critical_high)
    pval = np.abs(centers - null.mean) >= abs(null.u_obs - null.mean) - width / 2  # inclui o intervalo do U observado

    def bars(mask, name, fill, pattern=None):
        marker = dict(color=fill, line=dict(width=0))
        if pattern:
            marker["pattern"] = dict(shape=pattern, fgcolor=fill, bgcolor="rgba(0,0,0,0)")
        fig.add_trace(
            go.Bar(x=centers[mask], y=density[mask], width=width, name=name, marker=marker),
            row=1,
            col=2,
        )

    bars(np.ones_like(centers, dtype=bool), "Mann-Whitney: U sob H0", _rgba(color, 0.18))
    bars(reject, f"Mann-Whitney: região de rejeição (α = {alpha:.0%})", _rgba(color, 0.50))
    bars(pval, f"Mann-Whitney: área do p-valor (p = {null.p_value:.3f})", _rgba(color, 0.95))
    _observed(fig, null.u_obs, float(density.max()), f"U observado = {null.u_obs:.0f}", 2)
    fig.update_layout(barmode="overlay")


def _observed(fig: go.Figure, value: float, top: float, label: str, col: int) -> None:
    fig.add_trace(
        go.Scatter(
            x=[value, value],
            y=[0, top * 1.05],
            mode="lines",
            line=dict(color=OBSERVED_COLOR, width=2, dash="dash"),
            name=label,
        ),
        row=1,
        col=col,
    )


# --- G3 e G4: resultados de Q1/Q2/Q3 (lab04.robustness) -----------------------------------

SCENARIO_LABELS = {
    "lognormal_reference": "Lognormal ajustada (referência)",
    "outlier_contamination": "Com outliers",
}
TEST_KEYS = {"Welch": "welch", "Mann-Whitney": "mann_whitney"}
SCENARIO_DASH = {"lognormal_reference": "solid", "outlier_contamination": "dash"}
SCENARIO_SYMBOL = {"lognormal_reference": "circle", "outlier_contamination": "diamond"}


def _scenarios(report: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        scenarios = report["scenarios"]
        for key in SCENARIO_LABELS:
            scenarios[key]["q1_type_i"]
            scenarios[key]["q2"]
        report["repetitions"], report["alpha"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Resultados de Q3 incompletos: falta {exc}.") from exc
    return scenarios


def _mc_margin(p: float, repetitions: int) -> float:
    """Meia-largura (em %) do IC de 95% de uma proporção estimada por simulação."""
    return 100 * 1.96 * math.sqrt(max(p * (1 - p), 0.0) / repetitions)


def fig_g3(report: Mapping[str, Any]) -> go.Figure:
    """G3: erro tipo I de cada teste em cada situação simulada, com linha em α (Q1 e Q3).

    As barras de erro são o IC de 95% da proporção estimada, que reflete apenas o
    erro de simulação (com 10.000 repetições, cerca de ±0,4 ponto percentual).
    """
    scenarios = _scenarios(report)
    repetitions, alpha = int(report["repetitions"]), float(report["alpha"])
    situations = [SCENARIO_LABELS[key] for key in SCENARIO_LABELS]
    fig = go.Figure()
    for test, test_key in TEST_KEYS.items():
        rates = [float(scenarios[key]["q1_type_i"][test_key]) for key in SCENARIO_LABELS]
        fig.add_trace(
            go.Bar(
                x=situations,
                y=[100 * r for r in rates],
                name=test,
                marker=dict(color=TEST_COLORS[test]),
                error_y=dict(type="data", array=[_mc_margin(r, repetitions) for r in rates], color=TEXT, thickness=1.5),
                text=[f"{100 * r:.1f}%" for r in rates],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="#ffffff", size=14),
            )
        )
    fig.add_hline(
        y=100 * alpha,
        line=dict(color=OBSERVED_COLOR, width=2, dash="dash"),
        annotation_text=f"α nominal = {alpha:.0%}",
        annotation_position="top left",
    )
    top = max(100 * float(scenarios[k]["q1_type_i"][t]) for k in SCENARIO_LABELS for t in TEST_KEYS.values())
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_xaxes(title_text="Situação simulada (H0 verdadeira)")
    fig.update_yaxes(
        title_text="Erro tipo I (% de rejeições)",
        range=[0, max(top + _mc_margin(top / 100, repetitions), 100 * alpha) * 1.25],
        ticksuffix="%",
    )
    title = f"G3 — Erro tipo I de Welch e Mann-Whitney ({repetitions:,} repetições por situação)"
    return _style(fig, title, 460)


def fig_g4(report: Mapping[str, Any]) -> go.Figure:
    """G4: curvas de poder dos dois testes no mesmo gráfico (Q2 e Q3).

    Cor = teste (a mesma de G2 e G3); traço contínuo = referência, tracejado = outliers.
    O eixo x é o deslocamento em log(horas) do segundo grupo; o rótulo traz a razão das medianas.
    """
    scenarios = _scenarios(report)
    repetitions, alpha = int(report["repetitions"]), float(report["alpha"])
    effects = [float(e) for e in report["effects_log_shift"]]
    fig = go.Figure()
    for key, label in SCENARIO_LABELS.items():
        points = scenarios[key]["q2"]
        for test, test_key in TEST_KEYS.items():
            power = [100 * float(point["rejection_proportion"][test_key]) for point in points]
            fig.add_trace(
                go.Scatter(
                    x=effects,
                    y=power,
                    mode="lines+markers",
                    name=f"{test} — {label}",
                    line=dict(color=TEST_COLORS[test], width=2.5, dash=SCENARIO_DASH[key]),
                    marker=dict(size=8, symbol=SCENARIO_SYMBOL[key], color=TEST_COLORS[test]),
                    customdata=[math.exp(e) for e in effects],
                    hovertemplate="efeito %{x:.2f} (razão %{customdata:.2f}×)<br>rejeições %{y:.1f}%<extra></extra>",
                )
            )
    y_top = min(100.0, max(max(trace.y) for trace in fig.data) * 1.25 + 2)
    fig.add_hline(
        y=100 * alpha,
        line=dict(color=OBSERVED_COLOR, width=1.5, dash="dot"),
        annotation_text=f"α nominal = {alpha:.0%}",
        annotation_position="top left",
    )
    fig.update_xaxes(
        title_text="Tamanho do efeito: deslocamento em log(horas) do 2º grupo (razão de medianas)",
        tickvals=effects,
        ticktext=[f"{e:.1f} ({math.exp(e):.2f}×)" for e in effects],
    )
    fig.update_yaxes(title_text="Poder (% de rejeições de H0)", range=[0, y_top], ticksuffix="%")
    title = f"G4 — Curvas de poder de Welch e Mann-Whitney ({repetitions:,} repetições por efeito)"
    fig = _style(fig, title, 520)
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.25, x=0))
    return fig


def fig_power_complement(report: Mapping[str, Any]) -> go.Figure:
    """Complemento de G4 (#64): poder por tamanho amostral e por assimetria.

    À esquerda, o poder para o efeito observado nos dados reais em cada n por grupo,
    com a meta de 80%. À direita, o poder com n fixo quando só a assimetria (σ de
    log) muda e o efeito é o mesmo na escala log; a linha vertical marca os dados reais.
    """
    try:
        observed, skew = report["observed_effect"], report["skewness_sensitivity"]
        target, sigma_real = float(report["target_power"]), float(report["real_data_fit"]["sigma_log_hours"])
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Resultados de Q1/Q2 incompletos: falta {exc}.") from exc
    sizes = [int(row["n_per_group"]) for row in observed["power"]]
    sigmas = [float(row["sigma_log_hours"]) for row in skew["rows"]]
    fig = make_subplots(
        rows=1,
        cols=2,
        horizontal_spacing=0.10,
        subplot_titles=(
            f"Por n: efeito observado ({observed['geometric_mean_ratio']:.2f}×)",
            f"Por σ: n = {skew['n_per_group']}, efeito de {skew['standardized_effect']:g}σ",
        ),
    )
    for test, test_key in TEST_KEYS.items():
        line = dict(color=TEST_COLORS[test], width=2.5)
        fig.add_trace(
            go.Scatter(
                x=sizes,
                y=[100 * float(row["rejection_proportion"][test_key]) for row in observed["power"]],
                mode="lines+markers",
                name=test,
                legendgroup=test,
                line=line,
                hovertemplate="n = %{x}<br>poder %{y:.1f}%<extra>" + test + "</extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=sigmas,
                y=[100 * float(row["power"][test_key]) for row in skew["rows"]],
                mode="lines+markers",
                name=test,
                legendgroup=test,
                showlegend=False,
                line=line,
                hovertemplate="σ = %{x:.2f}<br>poder %{y:.1f}%<extra>" + test + "</extra>",
            ),
            row=1,
            col=2,
        )
    fig.add_hline(
        y=100 * target,
        line=dict(color=OBSERVED_COLOR, width=1.5, dash="dot"),
        annotation_text=f"meta de {target:.0%} de poder",
        annotation_position="top left",
        row=1,
        col=1,
    )
    fig.add_vline(
        x=sigma_real,
        line=dict(color=OBSERVED_COLOR, width=1.5, dash="dot"),
        annotation_text=f"dados reais (σ = {sigma_real:.2f})",
        annotation_position="top left",
        row=1,
        col=2,
    )
    fig.update_xaxes(
        title_text="PRs por grupo (escala log)", type="log", tickvals=sizes, ticktext=[str(n) for n in sizes],
        row=1, col=1,
    )
    fig.update_xaxes(title_text="Assimetria: σ de log(horas) (adimensional)", row=1, col=2)
    fig.update_yaxes(title_text="Poder (% de rejeições de H0)", range=[0, 100], ticksuffix="%", row=1, col=1)
    fig.update_yaxes(range=[0, 100], ticksuffix="%", row=1, col=2)
    return _style(fig, "Complemento de G4 — poder por tamanho amostral e assimetria (Q2)", 480)
