"""Poder e tamanho amostral do Lab05 (#76): quantas execuções por condição para 80% de poder.

Reaproveita do Lab04 o par Welch × Mann–Whitney vetorizado (``lab04.robustness``) e a regra
"menor n da grade que alcança a meta" (``lab04.power``). Diferenças em relação ao Lab04:

- cada modo de journal tem o seu próprio μ e σ de log(vazão), estimados do piloto e das
  verificações de validade, porque o Welch existe justamente para variâncias diferentes;
- o efeito é a razão WAL/DELETE (``exp`` do deslocamento em log), com o efeito mínimo de
  interesse de 5%;
- o nível de significância é 0,025, o menor limiar da correção de Holm com dois testes;
- além da lognormal, há um cenário com contaminação (execuções lentas ocasionais, como as
  do piloto) e um com σ no limite superior de confiança, já que σ vem de só 10 execuções.
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

from lab04.power import TARGET_POWER, TESTS, smallest_n_reaching
from lab04.robustness import _rejection_rates
from lab05.pilot import ROOT

DESIGN_RATIO = 1.05
DESIGN_ALPHA = 0.025  # 0,05 dividido entre as duas hipóteses principais (Holm, pior caso)
EFFECT_RATIOS = (1.0, 1.02, DESIGN_RATIO, 1.10, 1.25)
SAMPLE_SIZES = (5, 8, 10, 15, 20, 30, 40, 60, 80, 100, 150, 200, 300, 400, 600)
SCENARIOS = ("lognormal", "contaminada", "sigma_superior")
WARMUP_RUNS = 2
OUTLIER_Z = 3.0
SETUP_SECONDS = 0.05
MODES = ("delete", "wal")

# fonte: "pilot" ou "validation"; chaves de filtro correspondem a colunas do CSV.
METRICS = {
    "write_throughput": {
        "label": "Vazão de escrita (transações/s)", "role": "principal", "source": "pilot",
        "where": {"workload": "write"}, "column": "ops_per_second", "operations": 1000,
    },
    "read_throughput": {
        "label": "Vazão de leitura, 1 transação por consulta (consultas/s)", "role": "principal",
        "source": "pilot", "where": {"workload": "read"}, "column": "ops_per_second", "operations": 20_000,
    },
    "read_single_transaction": {
        "label": "Vazão de leitura em transação única (consultas/s)", "role": "sensibilidade",
        "source": "validation", "where": {"check": "read_transaction", "variant": "single"},
        "column": "ops_per_second", "operations": 20_000,
    },
    "write_fullfsync": {
        "label": "Vazão de escrita com F_FULLFSYNC (transações/s)", "role": "sensibilidade",
        "source": "validation", "where": {"check": "fullfsync", "variant": "on"},
        "column": "ops_per_second", "operations": 500,
    },
    "write_p95": {
        "label": "Latência p95 de escrita (ms)", "role": "secundária", "source": "pilot",
        "where": {"workload": "write"}, "column": "p95_ms", "operations": None,
    },
    "read_p95": {
        "label": "Latência p95 de leitura (ms)", "role": "secundária", "source": "pilot",
        "where": {"workload": "read"}, "column": "p95_ms", "operations": None,
    },
}
# Métricas que definem o n: as duas principais e a variante que testa a afirmação sobre leituras.
DESIGN_METRICS = ("write_throughput", "read_throughput", "read_single_transaction")
DESIGN_SCENARIOS = ("contaminada",)  # os outros dois são limites de sensibilidade


def load_conditions(pilot_path: str | Path, validation_path: str | Path) -> dict[str, dict[str, list[float]]]:
    """Valores de cada métrica por modo de journal, lidos dos CSVs do piloto e das verificações."""
    sources = {}
    for name, path in (("pilot", pilot_path), ("validation", validation_path)):
        with Path(path).open(newline="", encoding="utf-8") as stream:
            sources[name] = list(csv.DictReader(stream))
    conditions = {}
    for key, spec in METRICS.items():
        conditions[key] = {
            mode: [
                float(row[spec["column"]]) for row in sources[spec["source"]]
                if row["journal_mode"] == mode and all(row[k] == v for k, v in spec["where"].items())
            ]
            for mode in MODES
        }
    return conditions


def fit_group(values: Iterable[float]) -> dict[str, float]:
    """Parâmetros em log: média e DP (cenário lognormal); mediana, MAD e contaminação (robusto).

    Execuções com |z robusto| > 3 contam como contaminação: ``outlier_probability`` é a
    fração delas e ``outlier_log_shift`` o desvio médio em log em relação à mediana.
    """
    raw = np.asarray(list(values), dtype=float)
    if raw.size < 4 or not np.all(np.isfinite(raw)) or np.any(raw <= 0):
        raise ValueError("São necessárias pelo menos 4 observações positivas por grupo.")
    logged = np.log(raw)
    median = float(np.median(logged))
    mad = float(1.4826 * np.median(np.abs(logged - median)))
    sd = float(logged.std(ddof=1))
    robust_sigma = mad if mad > 0 else sd
    outliers = np.abs(logged - median) / robust_sigma > OUTLIER_Z if robust_sigma > 0 else np.zeros(logged.size, bool)
    return {
        "n": int(logged.size),
        "mean_log": float(logged.mean()),
        "sd_log": sd,
        "median_log": median,
        "robust_sigma_log": robust_sigma,
        "outlier_probability": float(outliers.mean()),
        "outlier_log_shift": float((logged[outliers] - median).mean()) if outliers.any() else 0.0,
    }


def sigma_upper_factor(n: int, confidence: float = 0.95) -> float:
    """Razão entre o limite superior unilateral do σ e o σ amostral, com n observações."""
    return math.sqrt((n - 1) / stats.chi2.ppf(1 - confidence, n - 1))


def pooled_contamination(fits: dict) -> dict[str, float]:
    """Ruído comum aos dois modos: σ robusto, frequência e desvio das execuções atípicas.

    Agrupar os modos mantém a hipótese nula verdadeira no cenário ``contaminada`` (mesma
    distribuição nos dois grupos quando a razão é 1), como o Lab04 faz com o σ agrupado.
    """
    groups = [fits["delete"], fits["wal"]]
    weight = sum(g["outlier_probability"] for g in groups)
    return {
        "robust_sigma_log": math.sqrt(sum(g["robust_sigma_log"] ** 2 for g in groups) / 2),
        "outlier_probability": weight / 2,
        "outlier_log_shift": sum(g["outlier_probability"] * g["outlier_log_shift"] for g in groups) / weight if weight else 0.0,
    }


def _sample(rng: np.random.Generator, fits: dict, mode: str, scenario: str, center: float,
            shape: tuple[int, int]) -> np.ndarray:
    """Amostras do cenário, todas centradas em ``center`` (a hipótese nula só difere do efeito)."""
    fit = fits[mode]
    if scenario == "lognormal":
        return rng.lognormal(center, fit["sd_log"], size=shape)
    if scenario == "sigma_superior":
        return rng.lognormal(center, fit["sd_log"] * sigma_upper_factor(fit["n"]), size=shape)
    if scenario == "contaminada":
        noise = pooled_contamination(fits)
        values = rng.lognormal(center, noise["robust_sigma_log"], size=shape)
        hit = rng.random(shape) < noise["outlier_probability"]
        return values * np.where(hit, math.exp(noise["outlier_log_shift"]), 1.0)
    raise ValueError(f"Cenário desconhecido: {scenario}.")


def _rates(rng, fits, scenario, n, ratio, repetitions, alpha) -> dict[str, float]:
    center = fits["delete"]["median_log"] if scenario == "contaminada" else fits["delete"]["mean_log"]
    first = _sample(rng, fits, "delete", scenario, center, (repetitions, n))
    second = _sample(rng, fits, "wal", scenario, center, (repetitions, n)) * ratio
    # O plano aplica o Welch a log(valores); o Mann–Whitney não muda com a transformação.
    return _rejection_rates(np.log(first), np.log(second), alpha)


def normal_approximation_n(fits: dict, ratio: float = DESIGN_RATIO, alpha: float = DESIGN_ALPHA,
                           power: float = TARGET_POWER) -> int:
    """n por grupo pela aproximação normal do Welch: (σ₁²+σ₂²)(z₁₋α/₂ + z_poder)² / δ²."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    variance = fits["delete"]["sd_log"] ** 2 + fits["wal"]["sd_log"] ** 2
    return math.ceil(variance * z**2 / math.log(ratio) ** 2)


def run_power(
    conditions: dict[str, dict[str, list[float]]],
    *,
    repetitions: int = 5_000,
    sample_sizes: Iterable[int] = SAMPLE_SIZES,
    ratios: Iterable[float] = EFFECT_RATIOS,
    metrics: Iterable[str] = tuple(METRICS),
    scenarios: Iterable[str] = SCENARIOS,
    seed: int = 42,
    alpha: float = DESIGN_ALPHA,
) -> dict:
    """Erro tipo I e poder por métrica, cenário, n e razão WAL/DELETE."""
    sample_sizes, ratios = tuple(int(n) for n in sample_sizes), tuple(float(r) for r in ratios)
    metrics, scenarios = tuple(metrics), tuple(scenarios)
    if repetitions < 100:
        raise ValueError("repetitions deve ser pelo menos 100.")
    if not sample_sizes or sample_sizes[0] < 2 or list(sample_sizes) != sorted(set(sample_sizes)):
        raise ValueError("sample_sizes deve ser crescente, sem repetições e com valores de pelo menos 2.")
    if not ratios or ratios[0] != 1.0 or any(not math.isfinite(r) or r < 1 for r in ratios):
        raise ValueError("ratios deve começar em 1 (hipótese nula) e conter valores de pelo menos 1.")
    if DESIGN_RATIO not in ratios:
        raise ValueError(f"ratios deve conter a razão de projeto {DESIGN_RATIO}.")
    if not 0 < alpha < 1 or seed < 0:
        raise ValueError("alpha deve estar entre 0 e 1 e seed deve ser não negativa.")
    unknown = [name for name in (*metrics, *scenarios) if name not in {*METRICS, *SCENARIOS}]
    if unknown:
        raise ValueError(f"Métrica ou cenário desconhecido: {unknown}.")

    rng = np.random.default_rng(seed)
    report_metrics = {}
    for key in metrics:
        fits = {mode: fit_group(conditions[key][mode]) for mode in MODES}
        observed_ratio = math.exp(fits["wal"]["mean_log"] - fits["delete"]["mean_log"])
        per_scenario = {}
        for scenario in scenarios:
            rows = [
                {"n_per_group": n, "ratio": r, "rejection_proportion": _rates(rng, fits, scenario, n, r, repetitions, alpha)}
                for n in sample_sizes for r in ratios
            ]
            at_design = [row for row in rows if row["ratio"] == DESIGN_RATIO]
            per_scenario[scenario] = {
                "rows": rows,
                "n_for_target_power": {test: smallest_n_reaching(at_design, test) for test in TESTS},
            }
        magnitude = max(observed_ratio, 1 / observed_ratio)
        observed = [
            {"n_per_group": n, "rejection_proportion": _rates(rng, fits, "lognormal", n, magnitude, repetitions, alpha)}
            for n in sample_sizes
        ]
        report_metrics[key] = {
            "label": METRICS[key]["label"],
            "role": METRICS[key]["role"],
            "fits": fits,
            "observed_ratio_wal_over_delete": observed_ratio,
            "observed_effect_power": observed,
            "n_for_target_power_observed_effect": {test: smallest_n_reaching(observed, test) for test in TESTS},
            "normal_approximation_n": normal_approximation_n(fits, alpha=alpha),
            "scenarios": per_scenario,
        }

    report = {
        "question": "Quantas execuções por condição para 80% de poder? (Lab05, #76)",
        "seed": seed,
        "repetitions": repetitions,
        "alpha": alpha,
        "alpha_note": "0,05 dividido por 2 hipóteses principais; o menor limiar da correção de Holm",
        "target_power": TARGET_POWER,
        "design_ratio": DESIGN_RATIO,
        "sample_sizes": list(sample_sizes),
        "ratios": list(ratios),
        "scenarios": {
            "lognormal": "lognormal com média e DP de log do piloto (inclui as execuções atípicas no σ)",
            "contaminada": "lognormal com σ robusto (MAD) e execuções atípicas ocasionais, com a frequência e o desvio vistos no piloto, iguais nos dois modos",
            "sigma_superior": "lognormal com σ no limite superior de 95% (qui-quadrado, 9 g.l. no piloto), por σ vir de 10 execuções",
        },
        "metrics": report_metrics,
    }
    report["decision"] = choose_n(report)
    return report


def choose_n(report: dict, warmup: int = WARMUP_RUNS) -> dict:
    """n por condição: o maior entre as métricas de projeto, no pior teste dos cenários de projeto.

    Para cada métrica e cenário de projeto vale o menor n da grade em que o teste com menos
    poder já alcança a meta; assim o n vale seja qual for o teste primário escolhido na análise.
    Se algum nunca alcança, usa o outro teste e registra a ressalva.
    """
    measured = {}
    for key in DESIGN_METRICS:
        if key not in report["metrics"]:
            continue
        for scenario in DESIGN_SCENARIOS:
            if scenario not in report["metrics"][key]["scenarios"]:
                continue
            needed = report["metrics"][key]["scenarios"][scenario]["n_for_target_power"]
            measured[f"{key}/{scenario}"] = needed
    if not measured:
        return {"analysis_n": None, "planned_runs": None, "binding": None, "per_case": {}}
    worst_test = {name: (None if None in n.values() else max(n.values())) for name, n in measured.items()}
    robust = {name: (n["mann_whitney"] if n["mann_whitney"] is not None else None) for name, n in measured.items()}
    usable = {name: (worst_test[name] if worst_test[name] is not None else robust[name]) for name in measured}
    if any(value is None for value in usable.values()):
        return {"analysis_n": None, "planned_runs": None, "binding": None, "per_case": usable,
                "note": "algum caso não alcança a meta na grade; ampliar a grade"}
    binding = max(usable, key=usable.get)
    return {
        "analysis_n": usable[binding],
        "warmup_runs": warmup,
        "planned_runs": usable[binding] + warmup,
        "binding": binding,
        "per_case": usable,
        "uses_robust_test_only": [name for name in usable if worst_test[name] is None],
    }


def time_budget(conditions: dict, planned_runs: int) -> dict:
    """Tempo estimado da coleta: execuções planejadas × tempo médio de cada condição."""
    items, total = [], 0.0
    for key, spec in METRICS.items():
        if spec["operations"] is None:
            continue
        seconds = {
            mode: spec["operations"] / float(np.mean(conditions[key][mode])) + SETUP_SECONDS for mode in MODES
        }
        subtotal = planned_runs * sum(seconds.values())
        total += subtotal
        items.append({"metric": key, "operations": spec["operations"], "seconds_per_run": seconds, "total_seconds": subtotal})
    return {"planned_runs_per_condition": planned_runs, "setup_seconds": SETUP_SECONDS, "items": items, "total_seconds": total}


def _verdict(rate: float, alpha: float, repetitions: int) -> str:
    margin = 1.96 * math.sqrt(rate * (1 - rate) / repetitions)
    if rate + margin < alpha:
        return "conservador"
    if rate - margin > alpha:
        return "liberal"
    return "compatível com α"


def type_i_summary(report: dict) -> dict:
    """Faixa do erro tipo I por teste (razão 1) e veredito, em todas as métricas e cenários."""
    summary = {}
    for test in TESTS:
        rates = [
            row["rejection_proportion"][test]
            for metric in report["metrics"].values() for scenario in metric["scenarios"].values()
            for row in scenario["rows"] if row["ratio"] == 1.0 and row["n_per_group"] >= 10
        ]
        summary[test] = {"min": min(rates), "max": max(rates),
                         "verdicts": sorted({_verdict(r, report["alpha"], report["repetitions"]) for r in rates})}
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=ROOT / "lab05" / "data" / "pilot.csv")
    parser.add_argument("--validation", type=Path, default=ROOT / "lab05" / "data" / "validation.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "lab05" / "data" / "power.json")
    parser.add_argument("--repetitions", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    conditions = load_conditions(args.pilot, args.validation)
    report = run_power(conditions, repetitions=args.repetitions, seed=args.seed)
    planned = report["decision"]["planned_runs"]
    report["type_i"] = type_i_summary(report)
    if planned is not None:
        report["time_budget"] = time_budget(conditions, planned)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    decision = report["decision"]
    print(f"n por condição (análise): {decision['analysis_n']}; execuções planejadas: {decision['planned_runs']}; "
          f"determinante: {decision['binding']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
