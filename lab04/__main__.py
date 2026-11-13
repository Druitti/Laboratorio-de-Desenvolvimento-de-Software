"""Valida os dados, gera resultados e abre o dashboard do Lab04."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_CSV = ROOT / "lab04" / "data" / "real_prs.csv"


def _run_module(module: str, *arguments: str) -> None:
    subprocess.run([sys.executable, "-m", module, *arguments], cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-per-group", type=int, default=30)
    parser.add_argument("--repetitions", type=int, default=10_000)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)

    _run_module("lab04.real_data")
    _run_module(
        "lab04.simulation", "--input", str(REAL_CSV), "--seed", str(args.seed),
        "--n-per-group", str(args.n_per_group), "--alpha", str(args.alpha),
    )
    _run_module(
        "lab04.power", "--input", str(REAL_CSV), "--seed", str(args.seed),
        "--repetitions", str(args.repetitions), "--alpha", str(args.alpha),
    )
    _run_module(
        "lab04.robustness", "--input", str(REAL_CSV), "--seed", str(args.seed),
        "--n-per-group", str(args.n_per_group), "--repetitions", str(args.repetitions),
        "--alpha", str(args.alpha),
    )
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "lab04" / "dashboard.py")],
        cwd=ROOT,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
