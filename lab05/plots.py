"""Esboço das visualizações do Lab05 (#76), feito com os dados do piloto.

São cinco figuras que a análise completa (#78) vai reaproveitar com os dados da coleta final:
F1 distribuição da vazão, F2 distribuição acumulada do p95 por execução, F3 razão WAL/DELETE
com IC de 95%, F4 curva de poder por n e F5 vazão ao longo das rodadas (deriva). Cada modo de
journal tem uma cor fixa em todas as figuras.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from lab05.analysis import geometric_ratio_ci  # noqa: E402
from lab05.pilot import ROOT  # noqa: E402
from lab05.power import DESIGN_RATIO, MODES, load_conditions  # noqa: E402

MODE_COLORS = {"delete": "#eb6834", "wal": "#2a78d6"}
MODE_NAMES = {"delete": "DELETE", "wal": "WAL"}
WORKLOAD_NAMES = {"write": "Escrita (transações/s)", "read": "Leitura (consultas/s)"}
GRID = "#e1e0d9"
FIGURES = {
    "f1_vazao.png": "F1",
    "f2_ecdf_p95.png": "F2",
    "f3_razao.png": "F3",
    "f4_poder.png": "F4",
    "f5_deriva.png": "F5",
}


def read_pilot(path: str | Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return [
            {**row, "round": int(row["round"]), "ops_per_second": float(row["ops_per_second"]),
             "p95_ms": float(row["p95_ms"])}
            for row in csv.DictReader(stream)
        ]


def _cell(rows: list[dict], workload: str, mode: str, key: str) -> list[float]:
    return [row[key] for row in rows if row["workload"] == workload and row["journal_mode"] == mode]


def _style(ax) -> None:
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def fig_f1(rows: list[dict]):
    """F1: vazão por condição (caixa + pontos de cada execução), eixo y em escala log."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    rng = np.random.default_rng(0)
    for ax, workload in zip(axes, ("write", "read")):
        for position, mode in enumerate(MODES):
            values = _cell(rows, workload, mode, "ops_per_second")
            ax.boxplot(values, positions=[position], widths=0.5, showfliers=False,
                       medianprops={"color": "black"}, boxprops={"color": MODE_COLORS[mode]},
                       whiskerprops={"color": MODE_COLORS[mode]}, capprops={"color": MODE_COLORS[mode]})
            ax.scatter(position + rng.uniform(-0.12, 0.12, len(values)), values, s=18, color=MODE_COLORS[mode], zorder=3)
        ax.set_yscale("log")
        ax.set_xticks(range(2), [MODE_NAMES[m] for m in MODES])
        ax.set_title(WORKLOAD_NAMES[workload])
        _style(ax)
    fig.suptitle("F1 — Vazão por execução (piloto, n = 10 por condição)")
    fig.tight_layout()
    return fig


def fig_f2(rows: list[dict]):
    """F2: distribuição acumulada do p95 de cada execução, por modo, eixo x em escala log."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, workload in zip(axes, ("write", "read")):
        for mode in MODES:
            values = np.sort(_cell(rows, workload, mode, "p95_ms"))
            ax.step(values, np.arange(1, values.size + 1) / values.size, where="post",
                    color=MODE_COLORS[mode], label=MODE_NAMES[mode])
        ax.set_xscale("log")
        ax.set_xlabel("p95 da execução (ms)")
        ax.set_title("Escrita" if workload == "write" else "Leitura")
        _style(ax)
    axes[0].set_ylabel("proporção das execuções")
    axes[0].legend(frameon=False)
    fig.suptitle("F2 — Distribuição acumulada do p95 por execução (piloto)")
    fig.tight_layout()
    return fig


def fig_f3(conditions: dict, *, seed: int = 42):
    """F3: razão das médias geométricas WAL/DELETE com IC 95% por bootstrap, escala log."""
    keys = [k for k in ("write_throughput", "write_fullfsync", "read_throughput", "read_single_transaction")]
    labels = ["Escrita", "Escrita, F_FULLFSYNC", "Leitura, 1 transação/consulta", "Leitura, transação única"]
    fig, ax = plt.subplots(figsize=(8, 4))
    for y, key in enumerate(reversed(keys)):
        ratio, low, high = geometric_ratio_ci(conditions[key]["wal"], conditions[key]["delete"], seed=seed)
        ax.errorbar(ratio, y, xerr=[[ratio - low], [high - ratio]], fmt="o", color=MODE_COLORS["wal"], capsize=4)
        ax.annotate(f"{ratio:.2f}×", (ratio, y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9)
    ax.axvline(1.0, color="black", linewidth=1)
    ax.axvspan(0.98, 0.99, color="#999999", alpha=0.5, label="documentação: leitura 1% a 2% mais lenta")
    ax.axvline(4.0, color="#7b4fa3", linestyle="--", label="Android em ext4: até 4×")
    ax.set_xscale("log")
    ticks = [0.9, 1, 1.5, 2, 3, 4, 5]
    ax.set_xticks(ticks, [f"{tick:g}" for tick in ticks])
    ax.minorticks_off()
    ax.set_yticks(range(len(keys)), list(reversed(labels)))
    ax.set_xlabel("razão WAL/DELETE (vezes mais rápido; > 1 favorece o WAL)")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    _style(ax)
    fig.suptitle("F3 — Razão WAL/DELETE com IC de 95% (piloto e verificações; n = 10)")
    fig.tight_layout()
    return fig


def fig_f4(report: dict):
    """F4: poder × n para a razão de projeto, nas métricas de projeto, cenário contaminado."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    styles = {"welch": "-", "mann_whitney": "--"}
    names = {"welch": "Welch (log)", "mann_whitney": "Mann–Whitney"}
    colors = {"write_throughput": "#1b9e77", "read_throughput": "#7b4fa3", "read_single_transaction": "#d95f02"}
    labels = {"write_throughput": "escrita", "read_throughput": "leitura", "read_single_transaction": "leitura, transação única"}
    for key, color in colors.items():
        rows = [r for r in report["metrics"][key]["scenarios"]["contaminada"]["rows"] if r["ratio"] == DESIGN_RATIO]
        for test, style in styles.items():
            ax.plot([r["n_per_group"] for r in rows], [r["rejection_proportion"][test] for r in rows],
                    style, color=color, marker="o", markersize=3, label=f"{labels[key]}, {names[test]}")
    ax.axhline(report["target_power"], color="black", linewidth=1)
    planned = report["decision"]["analysis_n"]
    if planned:
        ax.axvline(planned, color="#999999", linestyle=":")
        ax.text(planned, 1.04, f"n = {planned}", ha="center", fontsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("execuções por condição (n)")
    ax.set_ylabel(f"poder (α = {report['alpha']})")
    ax.set_ylim(0, 1.02)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    _style(ax)
    fig.suptitle(f"F4 — Poder para razão WAL/DELETE de {DESIGN_RATIO:g} (cenário contaminado)")
    fig.tight_layout()
    return fig


def fig_f5(rows: list[dict]):
    """F5: vazão ao longo das rodadas por condição, índice relativo à mediana da condição."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, workload in zip(axes, ("write", "read")):
        for mode in MODES:
            cell = [row for row in rows if row["workload"] == workload and row["journal_mode"] == mode]
            values = np.array([row["ops_per_second"] for row in cell])
            ax.plot([row["round"] for row in cell], values / np.median(values), marker="o", markersize=4,
                    color=MODE_COLORS[mode], label=MODE_NAMES[mode])
        ax.axhline(1.0, color="black", linewidth=0.8)
        ax.set_xlabel("rodada")
        ax.set_title("Escrita" if workload == "write" else "Leitura")
        _style(ax)
    axes[0].set_ylabel("vazão ÷ mediana da condição")
    axes[0].legend(frameon=False)
    fig.suptitle("F5 — Deriva ao longo da sessão (piloto)")
    fig.tight_layout()
    return fig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=ROOT / "lab05" / "data" / "pilot.csv")
    parser.add_argument("--validation", type=Path, default=ROOT / "lab05" / "data" / "validation.csv")
    parser.add_argument("--power", type=Path, default=ROOT / "lab05" / "data" / "power.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs" / "lab05" / "figuras")
    args = parser.parse_args(argv)
    rows = read_pilot(args.pilot)
    conditions = load_conditions(args.pilot, args.validation)
    report = json.loads(args.power.read_text(encoding="utf-8"))
    figures = {
        "f1_vazao.png": fig_f1(rows),
        "f2_ecdf_p95.png": fig_f2(rows),
        "f3_razao.png": fig_f3(conditions),
        "f4_poder.png": fig_f4(report),
        "f5_deriva.png": fig_f5(rows),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, fig in figures.items():
        fig.savefig(args.output_dir / name, dpi=150)
        plt.close(fig)
        print(f"{name} gravado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
