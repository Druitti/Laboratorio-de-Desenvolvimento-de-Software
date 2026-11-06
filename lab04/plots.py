"""Gráficos do dashboard do Lab04 (G1 e G2; G3 e G4 entram na S02).

Convenção de cores: cada *teste* tem uma cor fixa (``TEST_COLORS``) usada em
todos os gráficos; os *grupos* de dados (G1) usam uma paleta diferente para não
serem confundidos com os testes.
"""

from __future__ import annotations

from typing import Iterable, Mapping

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
