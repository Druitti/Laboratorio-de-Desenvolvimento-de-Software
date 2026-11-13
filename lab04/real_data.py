"""Carregamento e validação da amostra real de PRs do Lab04S01 (#61).

O CSV é autoexplicativo: cada linha traz fonte, método e limitações, além das
colunas ``group`` e ``value`` consumidas por ``lab04.simulation``. A validação
falha na primeira inconsistência, e o resumo traz os diagnósticos que justificam
o par de testes. ``analyze_real_groups`` aplica os dois testes aos dados reais
(seção 6 do dashboard, #67); a recomendação prévia foi registrada antes, em
``docs/lab04/cenario-dados.md``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "lab04" / "config.json"
DEFAULT_INPUT = ROOT / "lab04" / "data" / "real_prs.csv"
DEFAULT_FUNNEL = ROOT / "lab04" / "data" / "real_funnel.csv"
DEFAULT_SUMMARY = ROOT / "lab04" / "data" / "real_summary.json"

WITH_BOT = "with_review_bot"
WITHOUT_BOT = "without_review_bot"
GROUPS = (WITH_BOT, WITHOUT_BOT)
COLUMNS = [
    "group",
    "value",
    "repository",
    "pr_number",
    "source_url",
    "created_at",
    "merged_at",
    "review_bots",
    "additions",
    "deletions",
    "changed_files",
    "collected_at",
    "source",
    "method",
    "limitations",
]
_POSITIVE_INT_KEYS = ("frame_size", "min_minutes_to_merge", "max_prs_per_repository", "min_prs_per_group",
                      "n_per_group")


def parse_utc(value: str) -> datetime:
    """Converte um instante ISO 8601 com timezone para UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"A data {value!r} precisa incluir timezone.")
    return parsed.astimezone(timezone.utc)


def read_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in _POSITIVE_INT_KEYS:
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f"{key} deve ser inteiro positivo.")
    if type(config["seed"]) is not int or config["seed"] < 0:
        raise ValueError("seed deve ser inteiro não negativo.")
    if not parse_utc(config["window_start"]) < parse_utc(config["window_end"]) <= parse_utc(config["merged_before"]):
        raise ValueError("Esperado window_start < window_end <= merged_before.")
    if not config["review_bots"]:
        raise ValueError("review_bots não pode ser vazia.")
    return config


def load_real_data(path: str | Path = DEFAULT_INPUT, config: dict | None = None) -> list[dict]:
    """Lê o CSV e devolve as observações tipadas; levanta ValueError se inválido."""
    config = config or read_config()
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = sorted(set(COLUMNS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"Colunas ausentes no CSV: {', '.join(missing)}.")
        rows = [_read_row(row, line, config) for line, row in enumerate(reader, start=2)]
    _validate_sample(rows, config)
    return rows


def _read_row(row: dict, line: int, config: dict) -> dict:
    for column in COLUMNS:
        if column != "review_bots" and not (row.get(column) or "").strip():
            raise ValueError(f"Coluna {column!r} vazia na linha {line}.")
    group = row["group"]
    if group not in GROUPS:
        raise ValueError(f"Grupo desconhecido {group!r} na linha {line}.")
    try:
        value = float(row["value"])
        created_at, merged_at = parse_utc(row["created_at"]), parse_utc(row["merged_at"])
        pr_number = int(row["pr_number"])
        size = {key: int(row[key]) for key in ("additions", "deletions", "changed_files")}
    except ValueError as exc:
        raise ValueError(f"Valor inválido na linha {line}: {exc}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"O tempo na linha {line} deve ser finito e positivo.")
    hours = (merged_at - created_at).total_seconds() / 3600
    if not math.isclose(value, hours, abs_tol=1e-3):
        raise ValueError(f"value da linha {line} difere de merged_at - created_at ({hours:.4f} h).")
    if hours * 60 < config["min_minutes_to_merge"]:
        raise ValueError(f"O PR da linha {line} foi mergeado antes do tempo mínimo de exposição ao bot.")
    if not parse_utc(config["window_start"]) <= created_at < parse_utc(config["window_end"]):
        raise ValueError(f"created_at da linha {line} está fora da janela.")
    if merged_at >= parse_utc(config["merged_before"]):
        raise ValueError(f"merged_at da linha {line} é posterior ao corte da coleta.")
    if not re.fullmatch(rf"https://github\.com/{re.escape(row['repository'])}/pull/{pr_number}", row["source_url"]):
        raise ValueError(f"source_url da linha {line} não corresponde ao repositório e ao PR.")
    bots = [bot for bot in row["review_bots"].split(";") if bot]
    if group == WITH_BOT and not bots:
        raise ValueError(f"A linha {line} está em {WITH_BOT} sem bot de revisão.")
    if group == WITHOUT_BOT and bots:
        raise ValueError(f"A linha {line} está em {WITHOUT_BOT} mas registra bot de revisão.")
    unknown = sorted(set(bots) - set(config["review_bots"]))
    if unknown:
        raise ValueError(f"Bots fora da lista na linha {line}: {', '.join(unknown)}.")
    return {**row, **size, "value": value, "pr_number": pr_number, "review_bots": bots,
            "created_at": created_at, "merged_at": merged_at}


def _validate_sample(rows: list[dict], config: dict) -> None:
    sizes = Counter(row["group"] for row in rows)
    for group in GROUPS:
        if sizes[group] != config["n_per_group"]:
            raise ValueError(f"O grupo {group} tem {sizes[group]} observações; esperado {config['n_per_group']}.")
    repositories = Counter(row["repository"] for row in rows)
    repeated = sorted(repository for repository, count in repositories.items() if count > 1)
    if repeated:
        # Um PR por repositório sustenta a independência exigida pelos dois testes.
        raise ValueError(f"Repositórios com mais de uma observação: {', '.join(repeated)}.")


def summarize(rows: list[dict]) -> dict:
    """Descreve os grupos e calcula os diagnósticos usados na escolha dos testes."""
    values = {group: np.array([row["value"] for row in rows if row["group"] == group]) for group in GROUPS}
    first, second = values[WITH_BOT], values[WITHOUT_BOT]
    return {
        "unit": "horas entre a criação e o merge do PR",
        "groups": {group: _describe(group, values[group], rows) for group in GROUPS},
        "between_groups": {
            "variance_ratio_max_min": float(max(first.var(ddof=1), second.var(ddof=1))
                                            / min(first.var(ddof=1), second.var(ddof=1))),
            "brown_forsythe_p_hours": float(stats.levene(first, second, center="median").pvalue),
            "brown_forsythe_p_log_hours": float(stats.levene(np.log(first), np.log(second), center="median").pvalue),
        },
    }


def _describe(group: str, values: np.ndarray, rows: list[dict]) -> dict:
    members = [row for row in rows if row["group"] == group]
    q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75])
    logs = np.log(values)
    return {
        "n": int(values.size),
        "mean_hours": float(values.mean()),
        "std_hours": float(values.std(ddof=1)),
        "min_hours": float(values.min()),
        "q1_hours": float(q1),
        "median_hours": float(median),
        "q3_hours": float(q3),
        "max_hours": float(values.max()),
        "skewness": float(stats.skew(values, bias=False)),
        "excess_kurtosis": float(stats.kurtosis(values, bias=False)),
        "shapiro_p_hours": float(stats.shapiro(values).pvalue),
        "log_mean": float(logs.mean()),
        "log_std": float(logs.std(ddof=1)),
        "shapiro_p_log_hours": float(stats.shapiro(logs).pvalue),
        "median_changed_lines": float(np.median([row["additions"] + row["deletions"] for row in members])),
        "median_changed_files": float(np.median([row["changed_files"] for row in members])),
        "review_bots": dict(Counter(bot for row in members for bot in row["review_bots"]).most_common()),
    }


def summarize_funnel(path: str | Path = DEFAULT_FUNNEL) -> dict:
    """Totaliza o funil da coleta, repositório a repositório."""
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    counts = ("listed", WITH_BOT, WITHOUT_BOT, "excluded_author", "excluded_fast_merge", "excluded_ambiguous",
              "excluded_truncated")
    return {
        "repositories_in_frame": len(rows),
        "eligible_repositories": sum(row["eligible"] == "true" for row in rows),
        "sampled_repositories": sum(bool(row["sampled_pr"]) for row in rows),
        "prs": {key: sum(int(row[key]) for row in rows) for key in counts},
    }


def analyze_real_groups(samples: dict[str, list[float]], alpha: float = 0.05) -> dict:
    """Aplica Welch e Mann–Whitney aos dados reais e mede o tamanho do efeito de cada um.

    O primeiro grupo em ordem alfabética é o de referência das diferenças, como em
    ``compare_groups``: com os nomes da #61, diferenças positivas significam PRs com
    bot mais lentos.
    """
    from lab04.simulation import compare_groups

    result = compare_groups(samples, alpha=alpha)
    names = result["groups"]
    first, second = (np.asarray(samples[name], dtype=float) for name in names)
    n1, n2 = first.size, second.size
    v1, v2 = first.var(ddof=1), second.var(ddof=1)
    difference = float(first.mean() - second.mean())
    standard_error = math.sqrt(v1 / n1 + v2 / n2)
    df = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    margin = float(stats.t.ppf(1 - alpha / 2, df)) * standard_error
    pooled_sd = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    hedges_g = difference / pooled_sd * (1 - 3 / (4 * (n1 + n2) - 9))
    welch, mann_whitney = result["tests"]["welch"], result["tests"]["mann_whitney"]
    # O U do SciPy conta os pares em que o primeiro grupo supera o segundo.
    superiority = mann_whitney["statistic"] / (n1 * n2)
    return {
        "groups": names,
        "alpha": alpha,
        "welch": {
            "statistic": welch["statistic"],
            "df": float(df),
            "p_value": welch["p_value"],
            "mean_difference_hours": difference,
            "ci_hours": [difference - margin, difference + margin],
            "hedges_g": float(hedges_g),
            "conclusion": welch["interpretation"],
        },
        "mann_whitney": {
            "statistic": mann_whitney["statistic"],
            "p_value": mann_whitney["p_value"],
            "probability_of_superiority": float(superiority),
            "rank_biserial": float(2 * superiority - 1),
            "hodges_lehmann_hours": float(np.median(first[:, None] - second[None, :])),
            "conclusion": mann_whitney["interpretation"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--funnel", type=Path, default=DEFAULT_FUNNEL)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args(argv)
    try:
        rows = load_real_data(args.input, read_config(args.config))
    except ValueError as exc:
        print(f"Dados inválidos: {exc}", file=sys.stderr)
        return 1
    summary = {**summarize(rows), "funnel": summarize_funnel(args.funnel)}
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"OK: {len(rows)} observações válidas em {args.input}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
