#!/usr/bin/env python3
"""Cronometra um trial do Lab02 e registra o resultado em CSV."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KATAS_DIR = ROOT / "lab02" / "katas"
DEFAULT_CSV = ROOT / "lab02" / "data" / "trials.csv"
TIMEBOX_SECONDS = 35 * 60
CSV_FIELDS = [
    "data_hora_utc",
    "integrante",
    "kata",
    "tratamento",
    "tempo_segundos",
    "tempo_minutos",
    "censurado",
    "testes_passando",
    "testes_total",
    "testes_falhando",
    "taxa_sucesso",
]


def kata_path(kata: str) -> Path:
    path = KATAS_DIR / kata
    if not path.is_dir() or not (path / "test_kata.py").is_file():
        opcoes = ", ".join(sorted(p.name for p in KATAS_DIR.glob("k[0-9]*") if p.is_dir()))
        raise ValueError(f"Kata inexistente: {kata}. Opções disponíveis: {opcoes}")
    return path


def collect_total(path: Path) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "test_kata.py"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    match = re.search(r"(\d+) tests? collected", output)
    if not match:
        detail = output.strip() or "O pytest não retornou detalhes."
        raise RuntimeError(
            "Não foi possível coletar os testes. Saída do pytest:\n"
            f"{detail}\n\n"
            "Tente instalar as dependências com: python -m pip install -r requirements.txt"
        )
    return int(match.group(1))


def run_tests(path: Path, total: int) -> tuple[int, int, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "test_kata.py"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    passed_match = re.search(r"(\d+) passed", output)
    passed = int(passed_match.group(1)) if passed_match else 0
    return passed, result.returncode, output


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
        description="Cronometra um trial, executa pytest e salva o resultado em CSV."
    )
    parser.add_argument("--integrante", required=True, help="Nome ou usuário do integrante")
    parser.add_argument("--kata", required=True, help="Pasta do kata, por exemplo k1_merge_intervals")
    parser.add_argument(
        "--tratamento",
        required=True,
        choices=("com_ia", "sem_ia"),
        help="Tratamento usado no trial",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Arquivo CSV de saída")
    parser.add_argument("--intervalo", type=float, default=5.0, help="Segundos entre verificações")
    parser.add_argument(
        "--limite-minutos",
        type=float,
        default=35.0,
        help="Limite do trial; não pode ultrapassar 35 minutos",
    )
    args = parser.parse_args()
    if not 0 < args.limite_minutos <= 35:
        parser.error("--limite-minutos deve ser maior que 0 e no máximo 35")
    if args.intervalo <= 0:
        parser.error("--intervalo deve ser maior que 0")
    return args


def main() -> int:
    args = parse_args()
    try:
        path = kata_path(args.kata)
        total = collect_total(path)
    except (ValueError, RuntimeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2

    limit = min(args.limite_minutos * 60, TIMEBOX_SECONDS)
    started = time.monotonic()
    passed = 0
    green = False

    print(f"Trial iniciado: {args.kata} | {args.tratamento} | {total} testes")
    print(f"Time-box: {args.limite_minutos:g} min. Edite {path / 'kata.py'}.")
    print("Os testes serão verificados automaticamente.")
    print("Ctrl+C cancela o trial sem gravar uma medição inválida.")

    try:
        while True:
            passed, returncode, _ = run_tests(path, total)
            elapsed = time.monotonic() - started
            print(f"[{elapsed:7.1f}s] {passed}/{total} testes passando", flush=True)
            if returncode == 0 and passed == total:
                green = True
                break
            remaining = limit - elapsed
            if remaining <= 0:
                break
            time.sleep(min(args.intervalo, remaining))
    except KeyboardInterrupt:
        print("\nTrial cancelado pelo usuário. Nenhuma linha foi adicionada ao CSV.")
        return 130

    measured = time.monotonic() - started
    censored = not green
    recorded_seconds = limit if censored and measured >= limit else min(measured, limit)
    failures = max(total - passed, 0)
    rate = passed / total if total else 0.0
    row = {
        "data_hora_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "integrante": args.integrante,
        "kata": args.kata,
        "tratamento": args.tratamento,
        "tempo_segundos": f"{recorded_seconds:.2f}",
        "tempo_minutos": f"{recorded_seconds / 60:.2f}",
        "censurado": "sim" if censored else "nao",
        "testes_passando": passed,
        "testes_total": total,
        "testes_falhando": failures,
        "taxa_sucesso": f"{rate:.4f}",
    }
    save_csv(args.csv.resolve(), row)

    status = "GREEN" if green else "CENSURADO"
    print(f"Resultado: {status} | {passed}/{total} | {recorded_seconds:.2f}s")
    print(f"Registro salvo em: {args.csv.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
