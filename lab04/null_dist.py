"""Distribuição da estatística de cada teste sob H0 (insumo do gráfico G2).

Welch: sob H0 a estatística t segue, aproximadamente, uma t de Student com
graus de liberdade de Welch–Satterthwaite. Mann–Whitney: a distribuição de U
sob H0 é obtida por permutação dos grupos sobre os dados agrupados, o que vale
inclusive com empates. Ambos são bilaterais, como em ``lab04.simulation``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class WelchNull:
    """t de Welch sob H0: curva, valores críticos e o exemplo observado."""

    df: float
    x: np.ndarray
    density: np.ndarray
    critical: float  # região de rejeição: t <= -critical ou t >= +critical
    t_obs: float
    p_value: float


@dataclass(frozen=True)
class MannWhitneyNull:
    """U de Mann–Whitney sob H0 (permutação) e o exemplo observado."""

    u_null: np.ndarray
    mean: float
    critical_low: float  # região de rejeição: U <= critical_low ou U >= critical_high
    critical_high: float
    u_obs: float
    p_value: float
    n1: int
    n2: int


def split_groups(simulated: dict[str, Iterable[float]]) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Ordena os grupos como ``compare_groups`` (alfabética): estatística = 1º − 2º."""
    if len(simulated) != 2:
        raise ValueError("São necessários exatamente dois grupos.")
    names = sorted(simulated)
    first = np.asarray(list(simulated[names[0]]), dtype=float)
    second = np.asarray(list(simulated[names[1]]), dtype=float)
    if first.size < 2 or second.size < 2:
        raise ValueError("Cada grupo deve ter pelo menos duas observações.")
    return names, first, second


def welch_df(a: Iterable[float], b: Iterable[float]) -> float:
    """Graus de liberdade de Welch–Satterthwaite."""
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    va, vb = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    if va + vb == 0:
        raise ValueError("Variância nula nos dois grupos: t de Welch indefinido.")
    return float((va + vb) ** 2 / (va**2 / (a.size - 1) + vb**2 / (b.size - 1)))


def welch_null(
    a: Iterable[float], b: Iterable[float], *, alpha: float = 0.05, grid_points: int = 400
) -> WelchNull:
    """Curva t(gl) sob H0, valor crítico bilateral e p-valor do exemplo (a, b)."""
    _check_alpha(alpha)
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    df = welch_df(a, b)
    se = np.sqrt(a.var(ddof=1) / a.size + b.var(ddof=1) / b.size)
    t_obs = float((a.mean() - b.mean()) / se)
    dist = stats.t(df)
    limit = max(float(dist.ppf(0.9995)), abs(t_obs) * 1.15)
    x = np.linspace(-limit, limit, grid_points)
    return WelchNull(
        df=df,
        x=x,
        density=dist.pdf(x),
        critical=float(dist.ppf(1 - alpha / 2)),
        t_obs=t_obs,
        p_value=float(2 * dist.sf(abs(t_obs))),
    )


def mannwhitney_null(
    a: Iterable[float],
    b: Iterable[float],
    *,
    alpha: float = 0.05,
    n_perm: int = 10_000,
    seed: int = 42,
) -> MannWhitneyNull:
    """U₁ sob H0 por permutação; p-valor bilateral com correção (k+1)/(N+1)."""
    _check_alpha(alpha)
    if n_perm < 100:
        raise ValueError("n_perm deve ser pelo menos 100.")
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    n1, n2 = a.size, b.size
    ranks = stats.rankdata(np.concatenate([a, b]))  # postos médios tratam empates
    offset = n1 * (n1 + 1) / 2
    u_obs = float(ranks[:n1].sum() - offset)

    rng = np.random.default_rng(seed)
    permuted = rng.permuted(np.tile(ranks, (n_perm, 1)), axis=1)
    u_null = permuted[:, :n1].sum(axis=1) - offset

    mean = n1 * n2 / 2
    extreme = np.abs(u_null - mean) >= abs(u_obs - mean) - 1e-9
    return MannWhitneyNull(
        u_null=u_null,
        mean=mean,
        critical_low=float(np.quantile(u_null, alpha / 2)),
        critical_high=float(np.quantile(u_null, 1 - alpha / 2)),
        u_obs=u_obs,
        p_value=float((extreme.sum() + 1) / (n_perm + 1)),
        n1=n1,
        n2=n2,
    )


def _check_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise ValueError("alpha deve estar entre 0 e 1.")
