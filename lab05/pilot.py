"""Piloto de viabilidade do Lab05S01 (#74): SQLite com journal WAL × DELETE (rollback).

Cada execução cria um banco novo em um diretório temporário e mede uma carga de
escrita (transações de um único INSERT) ou de leitura (consultas por chave
primária). A ordem das quatro condições é sorteada em cada rodada, com semente
fixa, para que aquecimento e ruído da máquina não se confundam com o modo de
journal. Usa só a biblioteca padrão; a versão do SQLite é a do módulo ``sqlite3``.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL_MODES = ("delete", "wal")
WORKLOADS = ("write", "read")
PAYLOAD = "x" * 100
SYNCHRONOUS = "FULL"
COLUMNS = [
    "run_id",
    "round",
    "order_in_round",
    "journal_mode",
    "workload",
    "operations",
    "total_seconds",
    "ops_per_second",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "max_ms",
]


def percentile_ms(latencies_ns: list[int], percent: int) -> float:
    """Percentil (método inclusivo) das latências, em milissegundos."""
    if percent == 50:
        return statistics.median(latencies_ns) / 1e6
    return statistics.quantiles(latencies_ns, n=100, method="inclusive")[percent - 1] / 1e6


def run_once(
    journal_mode: str,
    workload: str,
    directory: str | Path,
    *,
    write_transactions: int,
    read_rows: int,
    read_queries: int,
    rng: random.Random,
    fullfsync: bool = False,
    single_transaction: bool = False,
) -> dict:
    """Executa uma condição num banco novo e devolve as métricas da execução.

    ``fullfsync`` liga o F_FULLFSYNC do macOS, que esvazia o cache do disco a cada
    sincronização; ``single_transaction`` faz todas as leituras numa única transação.
    Os dois existem para as verificações de validade de #79 e ficam desligados no piloto.
    """
    if journal_mode not in JOURNAL_MODES or workload not in WORKLOADS:
        raise ValueError(f"Condição inválida: {journal_mode}/{workload}.")
    path = Path(directory) / f"{journal_mode}-{workload}.db"
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        effective = connection.execute(f"PRAGMA journal_mode={journal_mode}").fetchone()[0]
        if effective != journal_mode:
            raise RuntimeError(f"O SQLite recusou journal_mode={journal_mode} (ficou {effective}).")
        connection.execute(f"PRAGMA synchronous={SYNCHRONOUS}")
        connection.execute(f"PRAGMA fullfsync={int(fullfsync)}")
        connection.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        latencies: list[int] = []
        if workload == "write":
            for _ in range(write_transactions):
                start = time.perf_counter_ns()
                connection.execute("BEGIN")
                connection.execute("INSERT INTO t (payload) VALUES (?)", (PAYLOAD,))
                connection.execute("COMMIT")
                latencies.append(time.perf_counter_ns() - start)
        else:
            connection.execute("BEGIN")
            connection.executemany("INSERT INTO t (payload) VALUES (?)", ((PAYLOAD,) for _ in range(read_rows)))
            connection.execute("COMMIT")
            keys = [rng.randrange(1, read_rows + 1) for _ in range(read_queries)]
            if single_transaction:
                connection.execute("BEGIN")
            for key in keys:
                start = time.perf_counter_ns()
                connection.execute("SELECT payload FROM t WHERE id = ?", (key,)).fetchone()
                latencies.append(time.perf_counter_ns() - start)
            if single_transaction:
                connection.execute("COMMIT")
    finally:
        connection.close()
    total = sum(latencies) / 1e9
    return {
        "journal_mode": journal_mode,
        "workload": workload,
        "operations": len(latencies),
        "total_seconds": total,
        "ops_per_second": len(latencies) / total,
        "p50_ms": percentile_ms(latencies, 50),
        "p95_ms": percentile_ms(latencies, 95),
        "p99_ms": percentile_ms(latencies, 99),
        "max_ms": max(latencies) / 1e6,
    }


def run_pilot(
    *,
    rounds: int = 10,
    seed: int = 5,
    write_transactions: int = 1000,
    read_rows: int = 10_000,
    read_queries: int = 5_000,
    base_dir: str | Path | None = None,
) -> list[dict]:
    """Roda ``rounds`` rodadas; cada uma executa as quatro condições em ordem sorteada."""
    if rounds < 1 or min(write_transactions, read_rows, read_queries) < 1:
        raise ValueError("rounds e os tamanhos das cargas devem ser positivos.")
    rng = random.Random(seed)
    conditions = [(mode, workload) for mode in JOURNAL_MODES for workload in WORKLOADS]
    rows = []
    for round_number in range(1, rounds + 1):
        order = rng.sample(conditions, len(conditions))
        for position, (mode, workload) in enumerate(order, start=1):
            # Diretório novo a cada execução: nenhum arquivo -wal, -shm ou -journal é reaproveitado.
            with tempfile.TemporaryDirectory(dir=base_dir) as directory:
                result = run_once(
                    mode, workload, directory, write_transactions=write_transactions,
                    read_rows=read_rows, read_queries=read_queries, rng=rng,
                )
            rows.append({"run_id": len(rows) + 1, "round": round_number, "order_in_round": position, **result})
    return rows


def environment(seed: int, parameters: dict) -> dict:
    """Registra o que pode afetar as medições, para reprodução e para as ameaças à validade."""
    probe = sqlite3.connect(":memory:")
    try:
        page_size = probe.execute("PRAGMA page_size").fetchone()[0]
        fullfsync = probe.execute("PRAGMA fullfsync").fetchone()[0]
    finally:
        probe.close()
    cpu = platform.processor()
    if sys.platform == "darwin":
        cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    return {
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sqlite_version": sqlite3.sqlite_version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "temp_dir": tempfile.gettempdir(),
        "pragmas": {"synchronous": SYNCHRONOUS, "page_size": page_size, "fullfsync": fullfsync},
        "payload_bytes": len(PAYLOAD),
        "seed": seed,
        "parameters": parameters,
    }


def summarize(rows: list[dict]) -> list[dict]:
    """Média, desvio-padrão e coeficiente de variação da vazão por condição."""
    summary = []
    for workload in WORKLOADS:
        for mode in JOURNAL_MODES:
            values = [row["ops_per_second"] for row in rows if row["journal_mode"] == mode and row["workload"] == workload]
            mean = statistics.fmean(values)
            sd = statistics.stdev(values) if len(values) > 1 else 0.0
            summary.append({
                "workload": workload,
                "journal_mode": mode,
                "runs": len(values),
                "mean_ops_per_second": mean,
                "sd_ops_per_second": sd,
                "cv": sd / mean,
                "median_p95_ms": statistics.median(
                    row["p95_ms"] for row in rows if row["journal_mode"] == mode and row["workload"] == workload
                ),
            })
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--write-transactions", type=int, default=1000)
    parser.add_argument("--read-rows", type=int, default=10_000)
    parser.add_argument("--read-queries", type=int, default=5_000)
    parser.add_argument("--output", type=Path, default=ROOT / "lab05" / "data" / "pilot.csv")
    parser.add_argument("--env", type=Path, default=ROOT / "lab05" / "data" / "pilot_env.json")
    args = parser.parse_args(argv)
    parameters = {
        "rounds": args.rounds,
        "write_transactions": args.write_transactions,
        "read_rows": args.read_rows,
        "read_queries": args.read_queries,
    }
    rows = run_pilot(seed=args.seed, **parameters)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows({key: (f"{value:.6g}" if isinstance(value, float) else value) for key, value in row.items()}
                         for row in rows)
    args.env.parent.mkdir(parents=True, exist_ok=True)
    args.env.write_text(json.dumps(environment(args.seed, parameters), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    for item in summarize(rows):
        print(
            f"{item['workload']:5} {item['journal_mode']:6} n={item['runs']:2} "
            f"vazão média {item['mean_ops_per_second']:10.1f} ops/s (DP {item['sd_ops_per_second']:8.1f}, "
            f"CV {item['cv']:.1%}); p95 mediano {item['median_p95_ms']:.4f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
