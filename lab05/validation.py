"""Verificações de validade do Lab05S02 (#79): quanto cada ameaça pesa nas medições.

São quatro checagens, cada uma ligada a uma ameaça da proposta:

- ``read_transaction`` (construto): leituras com uma transação por consulta, como no
  piloto, contra todas as leituras numa única transação.
- ``fullfsync`` (construto e externa): escritas com o ``fsync`` padrão do macOS contra
  o F_FULLFSYNC, que esvazia o cache do disco e dá a durabilidade real.
- ``overhead`` (construto): custo fixo de uma chamada Python → SQLite (``SELECT 1``),
  comparado às latências medidas.
- ``order`` (interna): correlação de postos entre a posição na rodada e a vazão, nos
  dados do piloto, para detectar aquecimento ou deriva.

A ordem das condições é sorteada em cada rodada, como no piloto.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

from lab05.pilot import JOURNAL_MODES, ROOT, percentile_ms, run_once

CHECK_COLUMNS = ["check", "variant", "journal_mode", "round", "ops_per_second", "p50_ms", "p95_ms"]


def spearman(x: list[float], y: list[float]) -> float:
    """Correlação de postos de Spearman (postos médios para empates)."""
    def ranks(values):
        order = sorted(range(len(values)), key=values.__getitem__)
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                result[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return result

    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def run_checks(
    *,
    rounds: int = 10,
    seed: int = 7,
    write_transactions: int = 500,
    read_rows: int = 10_000,
    read_queries: int = 20_000,
    base_dir: str | Path | None = None,
) -> list[dict]:
    """Executa as checagens ``read_transaction`` e ``fullfsync`` em rodadas com ordem sorteada."""
    rng = random.Random(seed)
    conditions = [
        ("read_transaction", variant, mode) for variant in ("per_query", "single") for mode in JOURNAL_MODES
    ] + [("fullfsync", variant, mode) for variant in ("off", "on") for mode in JOURNAL_MODES]
    rows = []
    for round_number in range(1, rounds + 1):
        for check, variant, mode in rng.sample(conditions, len(conditions)):
            options = (
                {"workload": "read", "single_transaction": variant == "single"}
                if check == "read_transaction"
                else {"workload": "write", "fullfsync": variant == "on"}
            )
            with tempfile.TemporaryDirectory(dir=base_dir) as directory:
                result = run_once(
                    mode, options.pop("workload"), directory, write_transactions=write_transactions,
                    read_rows=read_rows, read_queries=read_queries, rng=rng, **options,
                )
            rows.append({"check": check, "variant": variant, "journal_mode": mode, "round": round_number,
                         **{key: result[key] for key in ("ops_per_second", "p50_ms", "p95_ms")}})
    return rows


def call_overhead_ms(calls: int = 20_000) -> dict:
    """Latência de ``SELECT 1``: o piso de qualquer operação medida pelo Python."""
    connection = sqlite3.connect(":memory:")
    try:
        latencies = []
        for _ in range(calls):
            start = time.perf_counter_ns()
            connection.execute("SELECT 1").fetchone()
            latencies.append(time.perf_counter_ns() - start)
    finally:
        connection.close()
    return {"calls": calls, "p50_ms": percentile_ms(latencies, 50), "p95_ms": percentile_ms(latencies, 95)}


def order_effects(pilot_rows: list[dict]) -> list[dict]:
    """Spearman entre posição na rodada (e número da rodada) e vazão, por condição do piloto."""
    effects = []
    for workload in ("write", "read"):
        for mode in JOURNAL_MODES:
            cell = [row for row in pilot_rows if row["workload"] == workload and row["journal_mode"] == mode]
            throughput = [float(row["ops_per_second"]) for row in cell]
            effects.append({
                "workload": workload,
                "journal_mode": mode,
                "runs": len(cell),
                "rho_position": spearman([float(row["order_in_round"]) for row in cell], throughput),
                "rho_round": spearman([float(row["round"]) for row in cell], throughput),
            })
    return effects


def summarize(rows: list[dict]) -> dict:
    """Média da vazão por variante e modo, e a razão WAL/DELETE de cada variante."""
    summary = {}
    for check in ("read_transaction", "fullfsync"):
        variants = sorted({row["variant"] for row in rows if row["check"] == check})
        summary[check] = {}
        for variant in variants:
            means = {
                mode: statistics.fmean(
                    row["ops_per_second"] for row in rows
                    if row["check"] == check and row["variant"] == variant and row["journal_mode"] == mode
                )
                for mode in JOURNAL_MODES
            }
            summary[check][variant] = {
                "mean_ops_per_second": means,
                "wal_over_delete": means["wal"] / means["delete"],
            }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--pilot", type=Path, default=ROOT / "lab05" / "data" / "pilot.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "lab05" / "data" / "validation.csv")
    parser.add_argument("--summary", type=Path, default=ROOT / "lab05" / "data" / "validation_summary.json")
    args = parser.parse_args(argv)
    rows = run_checks(rounds=args.rounds, seed=args.seed)
    with args.pilot.open(newline="", encoding="utf-8") as stream:
        pilot_rows = list(csv.DictReader(stream))
    report = {
        "sqlite_version": sqlite3.sqlite_version,
        "seed": args.seed,
        "rounds": args.rounds,
        "checks": summarize(rows),
        "call_overhead": call_overhead_ms(),
        "order_effects": order_effects(pilot_rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CHECK_COLUMNS)
        writer.writeheader()
        writer.writerows({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in row.items()} for row in rows)
    args.summary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
