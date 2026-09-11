#!/usr/bin/env python3
"""Calcula métricas estáticas (Radon) de um kata e registra o resultado em CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze


ROOT = Path(__file__).resolve().parents[2]
KATAS_DIR = ROOT / "lab02" / "katas"
DEFAULT_CSV = ROOT / "lab02" / "data" / "static_metrics.csv"
CSV_FIELDS = [
    "data_hora_utc",
    "integrante",
    "kata",
    "tratamento",
    "arquivo",
    "loc",
    "lloc",
    "sloc",
    "comentarios",
    "linhas_em_branco",
    "complexidade_media",
    "complexidade_total",
    "num_blocos",
    "mi",
]


def kata_path(kata: str) -> Path:
    path = KATAS_DIR / kata
    if not path.is_dir() or not (path / "kata.py").is_file():
        opcoes = ", ".join(sorted(p.name for p in KATAS_DIR.glob("k[0-9]*") if p.is_dir()))
        raise ValueError(f"Kata inexistente: {kata}. Opções disponíveis: {opcoes}")
    return path


def compute_metrics(path: Path, incluir_mi: bool) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    raw = analyze(source)
    blocks = cc_visit(source)
    complexidades = [bloco.complexity for bloco in blocks]
    total = sum(complexidades)
    media = total / len(complexidades) if complexidades else 0.0
    mi = mi_visit(source, True) if incluir_mi else None
    return {
        "loc": raw.loc,
        "lloc": raw.lloc,
        "sloc": raw.sloc,
        "comentarios": raw.comments,
        "linhas_em_branco": raw.blank,
        "complexidade_media": media,
        "complexidade_total": total,
        "num_blocos": len(complexidades),
        "mi": mi,
    }


def save_csv(csv_path: Path, row: dict[str, object]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula métricas estáticas (Radon) de um kata e salva o resultado em CSV."
    )
    parser.add_argument("--kata", required=True, help="Pasta do kata, por exemplo k1_merge_intervals")
    parser.add_argument("--integrante", default="", help="Nome ou usuário do integrante")
    parser.add_argument(
        "--tratamento",
        choices=("com_ia", "sem_ia"),
        default=None,
        help="Tratamento do trial ao qual este kata.py pertence",
    )
    parser.add_argument("--mi", action="store_true", help="Também calcular o Índice de Manutenibilidade")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Arquivo CSV de saída")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        path = kata_path(args.kata)
    except ValueError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2

    arquivo = path / "kata.py"
    metricas = compute_metrics(arquivo, args.mi)
    row = {
        "data_hora_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "integrante": args.integrante,
        "kata": args.kata,
        "tratamento": args.tratamento or "",
        "arquivo": arquivo.relative_to(ROOT).as_posix(),
        "loc": metricas["loc"],
        "lloc": metricas["lloc"],
        "sloc": metricas["sloc"],
        "comentarios": metricas["comentarios"],
        "linhas_em_branco": metricas["linhas_em_branco"],
        "complexidade_media": f"{metricas['complexidade_media']:.2f}",
        "complexidade_total": metricas["complexidade_total"],
        "num_blocos": metricas["num_blocos"],
        "mi": f"{metricas['mi']:.2f}" if metricas["mi"] is not None else "",
    }
    save_csv(args.csv.resolve(), row)

    resumo_mi = f" | MI={row['mi']}" if row["mi"] else ""
    print(
        f"{args.kata}: LOC={row['loc']} | complexidade média={row['complexidade_media']}"
        f" ({row['num_blocos']} blocos){resumo_mi}"
    )
    print(f"Registro salvo em: {args.csv.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
