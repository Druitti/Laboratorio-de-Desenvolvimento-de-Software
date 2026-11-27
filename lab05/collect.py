"""Coleta local reproduzível para o Lab05 (#75)."""

import argparse
import csv
import json
import math
import os
import platform
import random
import sqlite3
import tempfile
from pathlib import Path

from lab05.pilot import COLUMNS, JOURNAL_MODES, PAGE_SIZE, WORKLOADS, environment, run_pilot


def validate_csv(path, *, rounds, seed, write_transactions, read_rows, read_queries):
    """Confere o esquema do piloto e o desenho da coleta no arquivo gravado."""
    conditions = [(mode, workload) for mode in JOURNAL_MODES for workload in WORKLOADS]
    rng = random.Random(seed)
    run_id = 0
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != COLUMNS:
            raise ValueError("Cabeçalho diferente do esquema do piloto.")

        for round_number in range(1, rounds + 1):
            order = rng.sample(conditions, len(conditions))
            for position, (mode, workload) in enumerate(order, 1):
                run_id += 1
                row = next(reader, None)
                operations = write_transactions if workload == "write" else read_queries
                expected = (str(run_id), str(round_number), str(position), mode, workload, str(operations))
                if row is None or None in row or tuple(row[key] for key in COLUMNS[:6]) != expected:
                    raise ValueError(f"Execução {run_id}: identificação, ordem ou carga inválida.")
                try:
                    seconds, throughput, p50, p95, p99, maximum = (
                        float(row[key]) for key in COLUMNS[6:]
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Execução {run_id}: métricas inválidas.") from exc
                metrics = (seconds, throughput, p50, p95, p99, maximum)
                if (
                    not all(math.isfinite(value) and value > 0 for value in metrics)
                    or not p50 <= p95 <= p99 <= maximum
                    or not math.isclose(throughput, operations / seconds, rel_tol=1e-5)
                ):
                    raise ValueError(f"Execução {run_id}: métricas incoerentes.")
                if workload == "read":
                    # O piloto usa o mesmo gerador para a ordem e as chaves de leitura.
                    for _ in range(read_queries):
                        rng.randrange(1, read_rows + 1)

        if next(reader, None) is not None:
            raise ValueError("O CSV contém execuções excedentes.")
    return run_id


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Diretório novo para o CSV e o JSON.")
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--warmup-rounds", type=int, default=1)
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--write-transactions", type=int, default=1000)
    parser.add_argument("--read-rows", type=int, default=10_000)
    parser.add_argument("--read-queries", type=int, default=5_000)
    parser.add_argument("--require-sqlite", help="Aborta se o Python usar outra versão do SQLite.")
    parser.add_argument("--storage", help="Dispositivo e sistema de arquivos do diretório de coleta.")
    parser.add_argument("--notes", help="Condições de execução e intercorrências, sem dados pessoais.")
    args = parser.parse_args(argv)
    parameters = {
        "rounds": args.rounds,
        "write_transactions": args.write_transactions,
        "read_rows": args.read_rows,
        "read_queries": args.read_queries,
    }
    if min(parameters.values()) < 1 or args.warmup_rounds < 0:
        parser.error("Rodadas e cargas devem ser positivas. O aquecimento pode ser zero.")
    if args.require_sqlite and sqlite3.sqlite_version != args.require_sqlite:
        parser.error(f"SQLite esperado {args.require_sqlite}, encontrado {sqlite3.sqlite_version}.")

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        parser.error(f"O diretório de saída já existe: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=output_dir.parent) as staging:
            staging = Path(staging)
            metadata = environment(args.seed, parameters)
            metadata["cpu"] = metadata["cpu"] or os.getenv("PROCESSOR_IDENTIFIER") or platform.machine()
            metadata.update(
                logical_cpus=os.cpu_count(),
                storage=args.storage,
                notes=args.notes,
                temp_dir="Mesmo volume do diretório de saída",
                warmup_rounds=args.warmup_rounds,
                warmup_seed=args.seed + 1,
            )
            metadata["pragmas"].update(page_size=PAGE_SIZE, fullfsync=0, journal_mode=JOURNAL_MODES)
            if args.warmup_rounds:
                warmup = {**parameters, "rounds": args.warmup_rounds}
                run_pilot(seed=args.seed + 1, base_dir=staging, **warmup)

            rows = run_pilot(seed=args.seed, base_dir=staging, **parameters)
            results = staging / "results"
            results.mkdir()
            csv_path = results / "collection.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            count = validate_csv(csv_path, seed=args.seed, **parameters)
            metadata["validated_rows"] = count
            (results / "environment.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            results.rename(output_dir)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(1, f"Falha na coleta: {exc}\n")
    print(f"{count} execuções validadas em {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
