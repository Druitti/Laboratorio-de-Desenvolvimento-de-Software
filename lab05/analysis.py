"""Análise de uma comparação WAL × DELETE (#76): teste e tamanho do efeito por métrica.

Todas as métricas do Lab05 estão em escala de razão, então são comparadas em log: a
diferença das médias de log é o log da razão entre as médias geométricas, e ``exp`` dela
é o "WAL é X vezes mais rápido". Este módulo reúne o que o plano de análise promete e é
reaproveitado pela análise completa (#78); no piloto serve só como exemplo ilustrativo.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from scipy import stats

BOOTSTRAP_REPETITIONS = 10_000


def _logs(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float)
    if array.size < 2 or not np.all(np.isfinite(array)) or np.any(array <= 0):
        raise ValueError("São necessárias pelo menos duas observações positivas por grupo.")
    return np.log(array)


def geometric_ratio_ci(
    wal: Iterable[float], delete: Iterable[float], *, repetitions: int = BOOTSTRAP_REPETITIONS,
    seed: int = 42, confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Razão WAL/DELETE das médias geométricas, com IC por bootstrap percentílico."""
    log_wal, log_delete = _logs(wal), _logs(delete)
    rng = np.random.default_rng(seed)
    first = rng.choice(log_wal, size=(repetitions, log_wal.size)).mean(axis=1)
    second = rng.choice(log_delete, size=(repetitions, log_delete.size)).mean(axis=1)
    tail = (1 - confidence) / 2
    low, high = np.quantile(first - second, [tail, 1 - tail])
    return math.exp(log_wal.mean() - log_delete.mean()), math.exp(low), math.exp(high)


def hedges_g(wal: Iterable[float], delete: Iterable[float]) -> float:
    """g de Hedges sobre log(valores): diferença padronizada com correção de viés."""
    a, b = _logs(wal), _logs(delete)
    dof = a.size + b.size - 2
    pooled = math.sqrt(((a.size - 1) * a.var(ddof=1) + (b.size - 1) * b.var(ddof=1)) / dof)
    if pooled == 0:
        return math.inf if a.mean() != b.mean() else 0.0
    return (a.mean() - b.mean()) / pooled * (1 - 3 / (4 * dof - 1))


def probability_of_superiority(wal: Iterable[float], delete: Iterable[float]) -> float:
    """P(WAL > DELETE) + metade dos empates, igual a U/(n1·n2) do Mann–Whitney."""
    a = np.asarray(list(wal), dtype=float)
    b = np.asarray(list(delete), dtype=float)
    greater = (a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()
    return float(greater / (a.size * b.size))


def compare(wal: Iterable[float], delete: Iterable[float], *, seed: int = 42) -> dict:
    """Welch (em log), Mann–Whitney, normalidade e tamanho do efeito de uma métrica."""
    wal, delete = list(wal), list(delete)
    log_wal, log_delete = _logs(wal), _logs(delete)
    ratio, low, high = geometric_ratio_ci(wal, delete, seed=seed)
    return {
        "n": {"wal": len(wal), "delete": len(delete)},
        "welch_p": float(stats.ttest_ind(log_wal, log_delete, equal_var=False).pvalue),
        "mann_whitney_p": float(stats.mannwhitneyu(wal, delete, alternative="two-sided").pvalue),
        "shapiro_p_log": {
            "wal": float(stats.shapiro(log_wal).pvalue),
            "delete": float(stats.shapiro(log_delete).pvalue),
        },
        "geometric_ratio": ratio,
        "ratio_ci95": [low, high],
        "hedges_g_log": hedges_g(wal, delete),
        "probability_of_superiority": probability_of_superiority(wal, delete),
    }


def holm(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Correção de Holm–Bonferroni: p ajustado e decisão para cada hipótese da família."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    adjusted, running = {}, 0.0
    for index, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - index) * p))
        adjusted[name] = {"p": p, "p_adjusted": running, "reject": running < alpha}
    return adjusted
