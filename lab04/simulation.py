"""Simulação e comparação de tempos de merge para o Lab04S01.

O cenário P1 compara o tempo até o merge de PRs com e sem bot de revisão.
Os dois grupos são independentes. Como tempos são positivos e assimétricos,
ajustamos uma lognormal a cada amostra real; comparamos Welch e Mann–Whitney
na mesma amostra simulada.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import stats


def read_real_samples(path: str | Path) -> dict[str, list[float]]:
    """Lê um CSV com colunas ``group`` e ``value`` (tempo positivo em horas)."""
    samples: dict[str, list[float]] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"group", "value"}.issubset(reader.fieldnames):
            raise ValueError("CSV precisa conter as colunas 'group' e 'value'.")
        for line, row in enumerate(reader, start=2):
            group = (row.get("group") or "").strip()
            if not group:
                raise ValueError(f"Grupo vazio na linha {line}.")
            try:
                value = float(row["value"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Valor inválido na linha {line}.") from exc
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"O tempo na linha {line} deve ser finito e positivo.")
            samples.setdefault(group, []).append(value)
    _validate_samples(samples)
    return samples


def _validate_samples(samples: dict[str, Iterable[float]]) -> None:
    if len(samples) != 2:
        raise ValueError("A amostra real deve conter exatamente dois grupos.")
    for group, values in samples.items():
        items = list(values)
        if len(items) < 2:
            raise ValueError(f"O grupo {group!r} precisa de pelo menos duas observações.")
        if any(not math.isfinite(float(x)) or float(x) <= 0 for x in items):
            raise ValueError(f"Todos os tempos do grupo {group!r} devem ser positivos e finitos.")


def simulate_groups(
    real_samples: dict[str, Iterable[float]], *, n_per_group: int = 30, seed: int = 42
) -> dict[str, np.ndarray]:
    """Gera amostras lognormais parametrizadas pela amostra real de cada grupo.

    ``sigma`` é o desvio-padrão amostral dos logaritmos; uma mesma semente e
    entrada produzem os mesmos valores, independentemente da ordem do dicionário.
    """
    real_samples = {group: list(values) for group, values in real_samples.items()}
    _validate_samples(real_samples)
    if n_per_group < 2:
        raise ValueError("n_per_group deve ser pelo menos 2.")
    if seed < 0:
        raise ValueError("seed deve ser não negativa.")

    rng = np.random.default_rng(seed)
    simulated: dict[str, np.ndarray] = {}
    for group in sorted(real_samples):
        values = np.asarray(list(real_samples[group]), dtype=float)
        log_values = np.log(values)
        mu = float(np.mean(log_values))
        sigma = float(np.std(log_values, ddof=1))
        simulated[group] = rng.lognormal(mean=mu, sigma=sigma, size=n_per_group)
    return simulated


def compare_groups(
    simulated: dict[str, Iterable[float]], *, alpha: float = 0.05
) -> dict[str, object]:
    """Executa Welch e Mann–Whitney bilateral sobre os mesmos dois grupos."""
    if not 0 < alpha < 1:
        raise ValueError("alpha deve estar entre 0 e 1.")
    simulated = {group: list(values) for group, values in simulated.items()}
    if len(simulated) != 2:
        raise ValueError("São necessários exatamente dois grupos simulados.")
    names = sorted(simulated)
    first = np.asarray(list(simulated[names[0]]), dtype=float)
    second = np.asarray(list(simulated[names[1]]), dtype=float)
    if first.size < 2 or second.size < 2:
        raise ValueError("Cada grupo simulado deve ter pelo menos duas observações.")
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("Os dados simulados devem ser finitos.")

    welch = stats.ttest_ind(first, second, equal_var=False, alternative="two-sided")
    mann_whitney = stats.mannwhitneyu(first, second, alternative="two-sided", method="auto")
    return {
        "groups": names,
        "alpha": alpha,
        "tests": {
            "welch": {
                "null_hypothesis": "as médias dos tempos dos dois grupos são iguais",
                "alternative_hypothesis": "as médias dos tempos dos dois grupos diferem",
                "statistic": _finite_number(welch.statistic),
                "p_value": _finite_number(welch.pvalue),
                "interpretation": _interpret(_finite_number(welch.pvalue), alpha),
            },
            "mann_whitney": {
                "null_hypothesis": "as distribuições dos tempos dos dois grupos são iguais",
                "alternative_hypothesis": "as distribuições dos tempos dos dois grupos diferem",
                "statistic": _finite_number(mann_whitney.statistic),
                "p_value": _finite_number(mann_whitney.pvalue),
                "interpretation": _interpret(_finite_number(mann_whitney.pvalue), alpha),
            },
        },
        "descriptive": {
            name: {
                "n": int(len(simulated[name])),
                "mean_hours": float(np.mean(np.asarray(simulated[name], dtype=float))),
                "median_hours": float(np.median(np.asarray(simulated[name], dtype=float))),
            }
            for name in names
        },
    }


def _finite_number(value: float) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def _interpret(p_value: float | None, alpha: float) -> str:
    if p_value is None:
        return "resultado inconclusivo: p-valor indefinido"
    if p_value < alpha:
        return f"rejeita H0 a {alpha:.0%}; há evidência de diferença entre os grupos"
    return f"não rejeita H0 a {alpha:.0%}; a amostra não mostrou evidência suficiente de diferença"


def run(real_samples: dict[str, Iterable[float]], *, n_per_group: int, seed: int, alpha: float):
    simulated = simulate_groups(real_samples, n_per_group=n_per_group, seed=seed)
    result = compare_groups(simulated, alpha=alpha)
    result["seed"] = seed
    result["distribution"] = "lognormal ajustada aos logaritmos da amostra real por grupo"
    result["direction"] = "bilateral"
    return simulated, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV real com group,value; value em horas")
    parser.add_argument("--output", type=Path, default=Path("lab04/data/simulated.csv"))
    parser.add_argument("--summary", type=Path, default=Path("lab04/data/comparison.json"))
    parser.add_argument("--n-per-group", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)

    simulated, summary = run(
        read_real_samples(args.input), n_per_group=args.n_per_group, seed=args.seed, alpha=args.alpha
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["group", "value_hours"])
        for group, values in simulated.items():
            writer.writerows((group, f"{value:.10g}") for value in values)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
