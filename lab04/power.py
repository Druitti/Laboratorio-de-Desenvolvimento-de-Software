"""Q1 e Q2 (#64): erro tipo I e poder de Welch e Mann–Whitney por efeito e tamanho amostral.

Os dois grupos vêm da lognormal ajustada à amostra real agrupada; sob H0 têm a mesma
distribuição. Os efeitos são deslocamentos em log(horas) no segundo grupo, de modo que
exp(efeito) é a razão entre as medianas. O módulo também estima o poder para o efeito
observado nos dados reais e mostra como a assimetria (σ de log) muda a vantagem entre
os testes. Q3, com outliers, fica em ``lab04.robustness``.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from lab04.robustness import DEFAULT_EFFECTS, _rejection_rates, pooled_lognormal_parameters
from lab04.simulation import read_real_samples

DEFAULT_SAMPLE_SIZES = (10, 20, 30, 60, 120, 240)
DEFAULT_SIGMAS = (0.1, 0.25, 0.5, 1.0, 1.5, 2.0)
STANDARDIZED_EFFECT = 0.5
SKEW_N = 30
TARGET_POWER = 0.8
TESTS = ("welch", "mann_whitney")
TEST_NAMES = {"welch": "Welch", "mann_whitney": "Mann–Whitney"}


def observed_log_shift(real: dict[str, Iterable[float]]) -> float:
    """Diferença absoluta entre as médias de log(horas) dos dois grupos reais."""
    groups = sorted(real)
    if len(groups) != 2:
        raise ValueError("A amostra real deve conter exatamente dois grupos.")
    means = [float(np.mean(np.log(np.asarray(list(real[g]), dtype=float)))) for g in groups]
    return abs(means[0] - means[1])


def smallest_n_reaching(rows: list[dict], test: str, target: float = TARGET_POWER) -> int | None:
    """Menor tamanho da grade cujo poder alcança ``target``; None se nenhum alcança."""
    reached = [row["n_per_group"] for row in rows if row["rejection_proportion"][test] >= target]
    return min(reached) if reached else None


def needed_n_text(report: dict, test: str) -> str:
    """Faixa da grade em que o poder para o efeito observado passa da meta."""
    sizes = report["sample_sizes"]
    n = report["observed_effect"]["n_for_target_power"][test]
    if n is None:
        return f"mais de {sizes[-1]}"
    index = sizes.index(n)
    return f"até {n}" if index == 0 else f"entre {sizes[index - 1]} e {n}"


def _rates(rng, mu: float, sigma: float, n: int, effect: float, repetitions: int, alpha: float) -> dict[str, float]:
    first = rng.lognormal(mu, sigma, size=(repetitions, n))
    second = rng.lognormal(mu, sigma, size=(repetitions, n)) * math.exp(effect)
    return _rejection_rates(first, second, alpha)


def run_power(
    real: dict[str, Iterable[float]],
    *,
    repetitions: int = 10_000,
    sample_sizes: Iterable[int] = DEFAULT_SAMPLE_SIZES,
    effects: Iterable[float] = DEFAULT_EFFECTS,
    sigmas: Iterable[float] = DEFAULT_SIGMAS,
    standardized_effect: float = STANDARDIZED_EFFECT,
    skew_n: int = SKEW_N,
    seed: int = 42,
    alpha: float = 0.05,
) -> dict[str, object]:
    """Executa Q1 e Q2 na grade de tamanhos amostrais e a análise de assimetria."""
    sample_sizes = tuple(int(n) for n in sample_sizes)
    effects = tuple(float(effect) for effect in effects)
    sigmas = tuple(float(s) for s in sigmas)
    if repetitions < 100:
        raise ValueError("repetitions deve ser pelo menos 100.")
    if not sample_sizes or any(n < 2 for n in sample_sizes) or list(sample_sizes) != sorted(set(sample_sizes)):
        raise ValueError("sample_sizes deve ser crescente, sem repetições e com valores de pelo menos 2.")
    if not effects or effects[0] != 0 or any(not math.isfinite(x) or x < 0 for x in effects):
        raise ValueError("effects deve começar em zero e conter valores não negativos.")
    if any(not math.isfinite(s) or s <= 0 for s in sigmas) or standardized_effect <= 0 or skew_n < 2:
        raise ValueError("Parâmetros da análise de assimetria inválidos.")
    if seed < 0:
        raise ValueError("seed deve ser não negativa.")
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha deve estar entre 0 e 1.")

    mu, sigma = pooled_lognormal_parameters(real)
    observed = observed_log_shift(real)
    rng = np.random.default_rng(seed)

    q2 = []
    for n in sample_sizes:
        for effect in effects:
            q2.append({
                "n_per_group": n,
                "effect_log_shift": effect,
                "median_ratio": math.exp(effect),
                "rejection_proportion": _rates(rng, mu, sigma, n, effect, repetitions, alpha),
            })
    observed_power = [
        {"n_per_group": n, "rejection_proportion": _rates(rng, mu, sigma, n, observed, repetitions, alpha)}
        for n in sample_sizes
    ]
    skew_rows = []
    # O σ ajustado entra na grade para marcar onde os dados reais estão.
    for s in sorted({*sigmas, sigma}):
        skew_rows.append({
            "sigma_log_hours": s,
            "is_real_fit": s == sigma,
            "type_i": _rates(rng, mu, s, skew_n, 0.0, repetitions, alpha),
            "power": _rates(rng, mu, s, skew_n, standardized_effect * s, repetitions, alpha),
        })

    report = {
        "question": "Q1 e Q2 — erro tipo I e poder por tamanho do efeito e tamanho amostral",
        "seed": seed,
        "repetitions": repetitions,
        "alpha": alpha,
        "target_power": TARGET_POWER,
        "real_data_fit": {"distribution": "lognormal", "mu_log_hours": mu, "sigma_log_hours": sigma},
        "null_hypothesis": "os dois grupos vêm da mesma lognormal",
        "effects_definition": "deslocamento em log(horas) do 2º grupo; razão de medianas = exp(efeito)",
        "sample_sizes": list(sample_sizes),
        "effects_log_shift": list(effects),
        "q1_type_i": [
            {"n_per_group": row["n_per_group"], "rejection_proportion": row["rejection_proportion"]}
            for row in q2
            if row["effect_log_shift"] == 0
        ],
        "q2_power": q2,
        "observed_effect": {
            "description": (
                "diferença entre as médias de log(horas) dos dois grupos reais; exp dela é a razão entre "
                "as médias geométricas, que no modelo lognormal é a razão entre as medianas"
            ),
            "log_shift": observed,
            "geometric_mean_ratio": math.exp(observed),
            "power": observed_power,
            "n_for_target_power": {test: smallest_n_reaching(observed_power, test) for test in TESTS},
        },
        "skewness_sensitivity": {
            "n_per_group": skew_n,
            "standardized_effect": standardized_effect,
            "description": (
                f"mesma mediana, σ de log variando; o efeito desloca log(horas) em {standardized_effect:g}σ, "
                "o que mantém fixo o tamanho do efeito na escala log"
            ),
            "rows": skew_rows,
        },
        "limitations": [
            "Os dois grupos usam o σ agrupado da amostra real; diferenças de forma entre os grupos ficam em Q3.",
            "O poder vale para a lognormal ajustada, cuja cauda é instável com 30 PRs por grupo.",
            "Os tamanhos amostrais formam uma grade; o n para 80% de poder é o menor valor da grade que atinge a meta.",
            "Mann–Whitney usa a aproximação normal com correção de continuidade, como em Q3.",
        ],
    }
    report["interpretation"] = interpret(report)
    return report


def _verdict(rate: float, alpha: float, repetitions: int) -> str:
    margin = 1.96 * math.sqrt(rate * (1 - rate) / repetitions)
    if rate + margin < alpha:
        return "conservador"
    if rate - margin > alpha:
        return "liberal"
    return "compatível com α"


def interpret(report: dict) -> str:
    alpha, reps = report["alpha"], report["repetitions"]
    pieces = []
    for test in TESTS:
        rates = [row["rejection_proportion"][test] for row in report["q1_type_i"]]
        verdicts = {_verdict(r, alpha, reps) for r in rates}
        pieces.append(
            f"{TEST_NAMES[test]}: erro tipo I entre {min(rates):.1%} e {max(rates):.1%} na grade de n "
            f"({', '.join(sorted(verdicts))})."
        )
    observed = report["observed_effect"]
    needed = [f"{TEST_NAMES[test]} {needed_n_text(report, test)}" for test in TESTS]
    pieces.append(
        f"Para o efeito observado (razão entre médias geométricas de {observed['geometric_mean_ratio']:.2f}×), "
        f"80% de poder exige {' e '.join(needed)} por grupo."
    )
    welch_wins = [
        row["sigma_log_hours"]
        for row in report["skewness_sensitivity"]["rows"]
        if row["power"]["welch"] >= row["power"]["mann_whitney"]
    ]
    if welch_wins:
        pieces.append(
            f"Welch tem poder igual ou maior que Mann–Whitney só com σ de log até {max(welch_wins):g}; "
            f"nos dados reais σ = {report['real_data_fit']['sigma_log_hours']:.2f}."
        )
    else:
        pieces.append("Mann–Whitney tem mais poder em todos os σ avaliados.")
    return " ".join(pieces)


def write_markdown(report: dict, path: str | Path) -> None:
    fit = report["real_data_fit"]
    lines = [
        "# Lab04S02 — Q1 e Q2: erro tipo I e poder (#64)",
        "",
        f"{report['repetitions']:,} repetições por combinação, α = {report['alpha']:.0%}, semente {report['seed']}. "
        f"Os dois grupos vêm da lognormal ajustada à amostra real agrupada (μ = {fit['mu_log_hours']:.3f}, "
        f"σ = {fit['sigma_log_hours']:.3f} em log(horas)). O efeito desloca log(horas) do 2º grupo; "
        "exp(efeito) é a razão entre as medianas.",
        "",
        "Reprodução: `python -m lab04.power` (ou `python -m lab04`, que também abre o dashboard).",
        "",
        "## Q1 — erro tipo I sob H0, por tamanho amostral",
        "",
        "| n por grupo | Welch | Mann–Whitney |",
        "|---:|---:|---:|",
    ]
    for row in report["q1_type_i"]:
        rates = row["rejection_proportion"]
        lines.append(f"| {row['n_per_group']} | {rates['welch']:.1%} | {rates['mann_whitney']:.1%} |")
    lines += ["", "## Q2 — poder por efeito e tamanho amostral", ""]
    header = "| Efeito log | Razão | " + " | ".join(
        f"W n={n} | MW n={n}" for n in report["sample_sizes"]
    ) + " |"
    lines += [header, "|---:|---:|" + "---:|" * (2 * len(report["sample_sizes"]))]
    for effect in report["effects_log_shift"]:
        cells = []
        for n in report["sample_sizes"]:
            row = next(r for r in report["q2_power"] if r["n_per_group"] == n and r["effect_log_shift"] == effect)
            cells += [f"{row['rejection_proportion']['welch']:.1%}", f"{row['rejection_proportion']['mann_whitney']:.1%}"]
        lines.append(f"| {effect:.2f} | {math.exp(effect):.2f}× | " + " | ".join(cells) + " |")
    observed = report["observed_effect"]
    lines += [
        "",
        "## Poder para o efeito observado nos dados reais",
        "",
        f"Efeito observado: {observed['log_shift']:.3f} em log(horas), razão entre médias geométricas de "
        f"{observed['geometric_mean_ratio']:.2f}× ({observed['description']}).",
        "",
        "| n por grupo | Welch | Mann–Whitney |",
        "|---:|---:|---:|",
    ]
    for row in observed["power"]:
        rates = row["rejection_proportion"]
        lines.append(f"| {row['n_per_group']} | {rates['welch']:.1%} | {rates['mann_whitney']:.1%} |")
    skew = report["skewness_sensitivity"]
    lines += [
        "",
        f"## Assimetria: quando a vantagem muda de lado (n = {skew['n_per_group']})",
        "",
        skew["description"][0].upper() + skew["description"][1:] + ".",
        "",
        "| σ de log | Erro tipo I Welch | Erro tipo I MW | Poder Welch | Poder MW |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in skew["rows"]:
        mark = " (dados reais)" if row["is_real_fit"] else ""
        lines.append(
            f"| {row['sigma_log_hours']:.2f}{mark} | {row['type_i']['welch']:.1%} | {row['type_i']['mann_whitney']:.1%} "
            f"| {row['power']['welch']:.1%} | {row['power']['mann_whitney']:.1%} |"
        )
    lines += ["", "## Interpretação", "", report["interpretation"], "", "## Limitações", ""]
    lines += [f"- {item}" for item in report["limitations"]]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("lab04/data/real_prs.csv"))
    parser.add_argument("--output", type=Path, default=Path("lab04/data/q1_q2.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/lab04/q1-q2.md"))
    parser.add_argument("--repetitions", type=int, default=10_000)
    parser.add_argument("--sample-sizes", type=int, nargs="+", default=list(DEFAULT_SAMPLE_SIZES))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)
    result = run_power(
        read_real_samples(args.input), repetitions=args.repetitions, sample_sizes=args.sample_sizes,
        seed=args.seed, alpha=args.alpha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(result, args.report)
    print(result["interpretation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
