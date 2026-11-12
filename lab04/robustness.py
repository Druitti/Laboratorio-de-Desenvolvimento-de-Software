"""Q3: erro tipo I e poder sob contaminação por outliers.

Compara o modelo lognormal ajustado à amostra real com uma condição não ideal
em que 5% dos tempos recebem um fator multiplicativo 20. Em ambas as condições,
H0 usa a mesma distribuição nos dois grupos; Q2 desloca a mediana do segundo grupo.
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

from lab04.simulation import read_real_samples

DEFAULT_EFFECTS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
OUTLIER_PROBABILITY = 0.05
OUTLIER_MULTIPLIER = 20.0


def pooled_lognormal_parameters(real: dict[str, Iterable[float]]) -> tuple[float, float]:
    """Estima μ e σ amostral de log(horas), agrupando as observações reais."""
    if len(real) != 2:
        raise ValueError("A amostra real deve conter exatamente dois grupos.")
    values = [float(value) for group in sorted(real) for value in real[group]]
    if len(values) < 4 or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("São necessárias pelo menos duas observações positivas por grupo.")
    logged = np.log(np.asarray(values, dtype=float))
    return float(logged.mean()), float(logged.std(ddof=1))


def _rejection_rates(first: np.ndarray, second: np.ndarray, alpha: float) -> dict[str, float]:
    """Calcula p-valores bilaterais de Welch e Mann–Whitney por linhas."""
    n1, n2 = first.shape[1], second.shape[1]
    mean1, mean2 = first.mean(axis=1), second.mean(axis=1)
    variance1, variance2 = first.var(axis=1, ddof=1), second.var(axis=1, ddof=1)
    component1, component2 = variance1 / n1, variance2 / n2
    standard_error = np.sqrt(component1 + component2)
    df = (component1 + component2) ** 2 / (
        component1**2 / (n1 - 1) + component2**2 / (n2 - 1)
    )
    t_statistic = (mean1 - mean2) / standard_error
    welch_p = 2 * stats.t.sf(np.abs(t_statistic), df)

    pooled_ranks = stats.rankdata(np.concatenate([first, second], axis=1), axis=1)
    u = pooled_ranks[:, :n1].sum(axis=1) - n1 * (n1 + 1) / 2
    u_mean = n1 * n2 / 2
    # Dados contínuos (lognormal com contaminação multiplicativa) não têm empates.
    u_variance = n1 * n2 * (n1 + n2 + 1) / 12
    z = np.maximum(np.abs(u - u_mean) - 0.5, 0) / math.sqrt(u_variance)
    mann_whitney_p = 2 * stats.norm.sf(z)
    return {
        "welch": float(np.mean(welch_p < alpha)),
        "mann_whitney": float(np.mean(mann_whitney_p < alpha)),
    }


def run_robustness(
    real: dict[str, Iterable[float]],
    *,
    repetitions: int = 10_000,
    n_per_group: int = 30,
    seed: int = 42,
    alpha: float = 0.05,
    effects: Iterable[float] = DEFAULT_EFFECTS,
    outlier_probability: float = OUTLIER_PROBABILITY,
    outlier_multiplier: float = OUTLIER_MULTIPLIER,
) -> dict[str, object]:
    """Executa Q1 e Q2 no ajuste real e com uma violação por outliers.

    Efeitos são deslocamentos em log(horas) no segundo grupo; ``exp(effect)`` é
    a razão entre as medianas. O efeito zero é reutilizado como estimativa de Q1.
    """
    mu, sigma = pooled_lognormal_parameters(real)
    effects = tuple(float(effect) for effect in effects)
    if repetitions < 100:
        raise ValueError("repetitions deve ser pelo menos 100.")
    if n_per_group < 2:
        raise ValueError("n_per_group deve ser pelo menos 2.")
    if seed < 0:
        raise ValueError("seed deve ser não negativa.")
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha deve estar entre 0 e 1.")
    if not effects or effects[0] != 0 or any(not math.isfinite(x) or x < 0 for x in effects):
        raise ValueError("effects deve começar em zero e conter valores não negativos.")
    if (
        not math.isfinite(outlier_probability)
        or not 0 <= outlier_probability <= 1
        or not math.isfinite(outlier_multiplier)
        or outlier_multiplier <= 1
    ):
        raise ValueError("Parâmetros de outlier inválidos.")

    rng = np.random.default_rng(seed)
    scenarios: dict[str, object] = {
        "lognormal_reference": {"description": "lognormal ajustada à amostra real", "q2": []},
        "outlier_contamination": {
            "description": (
                f"mistura com probabilidade {outlier_probability:.0%} de multiplicar cada tempo "
                f"por {outlier_multiplier:g}"
            ),
            "q2": [],
        },
    }

    for effect in effects:
        baseline_first = rng.lognormal(mu, sigma, size=(repetitions, n_per_group))
        baseline_second = rng.lognormal(mu, sigma, size=(repetitions, n_per_group)) * math.exp(effect)
        baseline_rates = _rejection_rates(baseline_first, baseline_second, alpha)

        contaminated_first = baseline_first * np.where(
            rng.random(baseline_first.shape) < outlier_probability, outlier_multiplier, 1.0
        )
        contaminated_second = baseline_second * np.where(
            rng.random(baseline_second.shape) < outlier_probability, outlier_multiplier, 1.0
        )
        contaminated_rates = _rejection_rates(contaminated_first, contaminated_second, alpha)

        for name, rates in (
            ("lognormal_reference", baseline_rates),
            ("outlier_contamination", contaminated_rates),
        ):
            scenarios[name]["q2"].append(
                {
                    "effect_log_shift": effect,
                    "second_group_median_ratio": math.exp(effect),
                    "rejection_proportion": rates,
                }
            )

    for scenario in scenarios.values():
        scenario["q1_type_i"] = scenario["q2"][0]["rejection_proportion"]

    report = {
        "question": "Q3 — efeito da contaminação por outliers no erro tipo I e no poder",
        "seed": seed,
        "repetitions": repetitions,
        "n_per_group": n_per_group,
        "alpha": alpha,
        "effects_definition": "deslocamento em log(horas); razão de medianas = exp(efeito)",
        "effects_log_shift": list(effects),
        "real_data_fit": {"distribution": "lognormal", "mu_log_hours": mu, "sigma_log_hours": sigma},
        "null_hypothesis": "os dois grupos vêm da mesma distribuição",
        "alternative_hypothesis": "os grupos diferem; os efeitos simulados elevam o tempo do segundo grupo",
        "tests": {
            "welch": "t de Welch bilateral para médias; estatística t e gl de Welch–Satterthwaite",
            "mann_whitney": "Mann–Whitney bilateral assintótico, com correção de continuidade",
        },
        "outlier_model": {"probability_per_observation": outlier_probability, "multiplier": outlier_multiplier},
        "scenarios": scenarios,
        "interpretation": _interpret(scenarios, alpha),
        "limitations": [
            "O modelo de contaminação é uma condição simulada, não uma afirmação sobre a frequência real de outliers.",
            "Welch e Mann–Whitney são avaliados sob o mesmo modelo e a mesma amostra de entrada.",
            "Mann–Whitney usa aproximação normal assintótica; a interpretação de localização requer formas semelhantes.",
            "As simulações estimam erro tipo I e poder do modelo, não causalidade do uso de bots.",
        ],
    }
    return report


def _interpret(scenarios: dict[str, object], alpha: float) -> str:
    reference = scenarios["lognormal_reference"]["q1_type_i"]
    outliers = scenarios["outlier_contamination"]["q1_type_i"]
    pieces = []
    for test in ("welch", "mann_whitney"):
        base = reference[test]
        contaminated = outliers[test]
        change_pp = (contaminated - base) * 100
        pieces.append(
            f"{test}: erro tipo I {base:.1%} no modelo de referência e {contaminated:.1%} "
            f"com outliers (variação {change_pp:+.1f} pontos percentuais; alfa={alpha:.0%})."
        )
    contaminated_power = scenarios["outlier_contamination"]["q2"]
    reference_power = scenarios["lognormal_reference"]["q2"]
    strongest = contaminated_power[-1]["rejection_proportion"]
    reference_strongest = reference_power[-1]["rejection_proportion"]
    pieces.append(
        "No maior efeito simulado, poder na referência e com outliers: "
        f"Welch {reference_strongest['welch']:.1%} e {strongest['welch']:.1%}; "
        f"Mann–Whitney {reference_strongest['mann_whitney']:.1%} e {strongest['mann_whitney']:.1%}."
    )
    return " ".join(pieces)


def write_markdown(report: dict[str, object], path: str | Path) -> None:
    scenarios = report["scenarios"]
    lines = [
        "# Lab04S02 — Q3: assimetria e outliers",
        "",
        f"{report['repetitions']:,} repetições por efeito, n={report['n_per_group']} por grupo, "
        f"α={report['alpha']:.0%}, semente {report['seed']}. Os efeitos são deslocamentos em "
        "log(horas); a razão de medianas do segundo grupo é exp(efeito).",
        "",
        "O cenário de referência usa uma lognormal ajustada à amostra real. O cenário não ideal "
        f"multiplica por {report['outlier_model']['multiplier']:g} cada observação com probabilidade "
        f"{report['outlier_model']['probability_per_observation']:.0%}, igualmente nos dois grupos sob H0.",
        "",
        "## Q1 — erro tipo I sob H0",
        "",
        "| Condição | Welch | Mann–Whitney | Referência α |",
        "|---|---:|---:|---:|",
    ]
    for key, label in (("lognormal_reference", "Lognormal de referência"), ("outlier_contamination", "Com outliers")):
        rates = scenarios[key]["q1_type_i"]
        lines.append(f"| {label} | {rates['welch']:.1%} | {rates['mann_whitney']:.1%} | {report['alpha']:.0%} |")
    lines.extend(["", "## Q2/Q3 — poder por tamanho do efeito", "", "| Efeito log | Razão das medianas | Welch referência | MW referência | Welch outliers | MW outliers |", "|---:|---:|---:|---:|---:|---:|"])
    for i, effect in enumerate(report["effects_log_shift"]):
        ratio = math.exp(effect)
        ref = scenarios["lognormal_reference"]["q2"][i]["rejection_proportion"]
        out = scenarios["outlier_contamination"]["q2"][i]["rejection_proportion"]
        lines.append(f"| {effect:.2f} | {ratio:.2f}× | {ref['welch']:.1%} | {ref['mann_whitney']:.1%} | {out['welch']:.1%} | {out['mann_whitney']:.1%} |")
    lines.extend(["", "## Interpretação", "", report["interpretation"], "", "A condição de referência também é assimétrica; Q3 mede o acréscimo de uma cauda ainda mais pesada pela contaminação especificada. Compare erro tipo I com α antes de comparar poder. As conclusões valem para este modelo e estes tamanhos amostrais, não para todos os dados de tempo de PR.", "", "## Limitações", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("lab04/data/real_prs.csv"))
    parser.add_argument("--output", type=Path, default=Path("lab04/data/q3_robustness.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/lab04/q3-robustness.md"))
    parser.add_argument("--repetitions", type=int, default=10_000)
    parser.add_argument("--n-per-group", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--outlier-probability", type=float, default=OUTLIER_PROBABILITY)
    parser.add_argument("--outlier-multiplier", type=float, default=OUTLIER_MULTIPLIER)
    args = parser.parse_args(argv)
    result = run_robustness(
        read_real_samples(args.input), repetitions=args.repetitions, n_per_group=args.n_per_group,
        seed=args.seed, alpha=args.alpha, outlier_probability=args.outlier_probability,
        outlier_multiplier=args.outlier_multiplier,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(result, args.report)
    print(result["interpretation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
