#!/usr/bin/env python3
"""Dashboard (RQ1/RQ2/RQ3) do Lab02: gera gráficos e um resumo de mediana/IQR
comparando com_ia vs sem_ia a partir de trials.csv e static_metrics.csv."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRIALS_CSV = ROOT / "lab02" / "data" / "trials.csv"
DEFAULT_METRICAS_CSV = ROOT / "lab02" / "data" / "static_metrics.csv"
DEFAULT_OUT_DIR = ROOT / "lab02" / "dashboard"

CHAVE = ["integrante", "kata", "tratamento"]

COLUNAS_TRIALS = {
    "data_hora_utc", "integrante", "kata", "tratamento", "tempo_segundos",
    "tempo_minutos", "censurado", "testes_passando", "testes_total",
    "testes_falhando", "taxa_sucesso",
}
COLUNAS_METRICAS = {
    "data_hora_utc", "integrante", "kata", "tratamento", "arquivo", "loc",
    "lloc", "sloc", "comentarios", "linhas_em_branco", "complexidade_media",
    "complexidade_total", "num_blocos", "mi",
}

# Ordem fixa (nunca alternar por dado) e paleta categórica validada
# (CVD-safe) para os 2 tratamentos — ver docs da skill dataviz.
ORDEM_TRATAMENTOS = ["sem_ia", "com_ia"]
PALETA = {"sem_ia": "#2a78d6", "com_ia": "#eb6834"}
ROTULOS_TRATAMENTO = {"sem_ia": "Sem IA", "com_ia": "Com IA"}

INTEGRANTES_ORDEM = ["Druitti", "gabsant07", "tavares"]
INTEGRANTES_ROTULOS = {"Druitti": "Ferreira", "gabsant07": "Santiago", "tavares": "Tavares"}

# Par divergente azul<->vermelho com meio-tom neutro, para correlação (-1..+1):
# ver skill dataviz (diverging pair blue<->red, midpoint gray).
DIVERGENTE_CORRELACAO = mcolors.LinearSegmentedColormap.from_list(
    "divergente_azul_vermelho", ["#2a78d6", "#f0efec", "#e34948"]
)


def aplicar_estilo() -> None:
    """Tema claro consistente para todos os gráficos do dashboard."""
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb",
        "axes.facecolor": "#fcfcfb",
        "savefig.facecolor": "#fcfcfb",
        "axes.edgecolor": "#c3c2b7",
        "axes.labelcolor": "#0b0b0b",
        "text.color": "#0b0b0b",
        "xtick.color": "#52514e",
        "ytick.color": "#52514e",
        "grid.color": "#e1e0d9",
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
    })


aplicar_estilo()


def carregar_trials(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    faltando = COLUNAS_TRIALS - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes em {csv_path}: {sorted(faltando)}")
    return df


def carregar_metricas(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    faltando = COLUNAS_METRICAS - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes em {csv_path}: {sorted(faltando)}")
    return df


def resumo_mediana_iqr(df: pd.DataFrame, coluna: str, por: str = "tratamento") -> pd.DataFrame:
    """Média, mediana, Q1, Q3, IQR e n de `coluna`, agrupados por `por`.

    A média é incluída só para contraste com a mediana: métricas de software
    (tempo, LOC, complexidade) costumam ser assimétricas à direita, e a
    distância entre média e mediana é o próprio sinal dessa assimetria — por
    isso a mediana/IQR é a métrica primária reportada, não a média.
    """
    grupo = df.groupby(por)[coluna]
    resumo = grupo.agg(n="count", media="mean", mediana="median")
    resumo["q1"] = grupo.quantile(0.25)
    resumo["q3"] = grupo.quantile(0.75)
    resumo["iqr"] = resumo["q3"] - resumo["q1"]
    resumo = resumo.reset_index()
    if por == "tratamento":
        ordem = [t for t in ORDEM_TRATAMENTOS if t in resumo[por].values]
        resumo = resumo.set_index(por).loc[ordem].reset_index()
    return resumo


def mesclar_trials_e_metricas(trials_df: pd.DataFrame, metricas_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Junta trials e métricas por (integrante, kata, tratamento).

    Retorna (completos, faltantes): `faltantes` lista trials/métricas sem par,
    para o chamador decidir como avisar (não deve mais ocorrer após a Issue
    #16 preencher o gap do Santiago, mas o merge fica robusto a isso).
    """
    merged = trials_df.merge(metricas_df, on=CHAVE, how="outer", suffixes=("_trial", "_metrica"), indicator=True)
    completos = merged[merged["_merge"] == "both"].drop(columns="_merge").reset_index(drop=True)
    faltantes = merged[merged["_merge"] != "both"].drop(columns="_merge").reset_index(drop=True)
    return completos, faltantes


def _boxplot_com_mediana(df: pd.DataFrame, coluna: str, ax: plt.Axes, titulo: str, ylabel: str, escala_log: bool = False) -> None:
    sns.boxplot(
        data=df, x="tratamento", y=coluna, hue="tratamento",
        order=ORDEM_TRATAMENTOS, hue_order=ORDEM_TRATAMENTOS,
        palette=PALETA, legend=False, width=0.5, showfliers=False, ax=ax,
    )
    sns.stripplot(
        data=df, x="tratamento", y=coluna, order=ORDEM_TRATAMENTOS,
        color="#0b0b0b", alpha=0.6, size=5, jitter=0.15, ax=ax,
    )
    if escala_log:
        ax.set_yscale("log")
    medianas = df.groupby("tratamento")[coluna].median()
    for i, trat in enumerate(ORDEM_TRATAMENTOS):
        if trat in medianas.index:
            ax.annotate(
                f"{medianas[trat]:.1f}", xy=(i, medianas[trat]), xytext=(14, 0),
                textcoords="offset points", ha="left", va="center", fontsize=9,
                fontweight="bold", color="#0b0b0b",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="#fcfcfb", edgecolor="none", alpha=0.85),
            )
    ax.set_xticks(range(len(ORDEM_TRATAMENTOS)))
    ax.set_xticklabels([ROTULOS_TRATAMENTO[t] for t in ORDEM_TRATAMENTOS])
    ax.set_xlabel("")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)


def _barplot_com_rotulo(df: pd.DataFrame, coluna: str, ax: plt.Axes, titulo: str, ylabel: str, formato_percentual: bool = False) -> None:
    sns.barplot(
        data=df, x="tratamento", y=coluna, hue="tratamento",
        order=ORDEM_TRATAMENTOS, hue_order=ORDEM_TRATAMENTOS,
        palette=PALETA, legend=False, errorbar=None, width=0.5, ax=ax,
    )
    valores = df.groupby("tratamento")[coluna].median()
    for i, trat in enumerate(ORDEM_TRATAMENTOS):
        if trat in valores.index:
            valor = valores[trat]
            texto = f"{valor:.0%}" if formato_percentual else f"{valor:.2f}"
            ax.annotate(
                texto, xy=(i, valor), xytext=(0, 6), textcoords="offset points",
                ha="center", fontsize=10, fontweight="bold", color="#0b0b0b",
            )
    if formato_percentual:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
        ax.set_ylim(0, 1.15)
    ax.set_xticks(range(len(ORDEM_TRATAMENTOS)))
    ax.set_xticklabels([ROTULOS_TRATAMENTO[t] for t in ORDEM_TRATAMENTOS])
    ax.set_xlabel("")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)


def _fonte(fig: plt.Figure, texto: str) -> None:
    """Rodapé com a fonte/N dos dados — mesmo padrão de citação usado em todo
    material de referência de visualização (Fonte: <dataset> — <amostra>)."""
    fig.text(0.01, 0.01, texto, fontsize=8, color="#898781", ha="left", va="bottom")


def _resumo_n(df: pd.DataFrame) -> str:
    contagem = df["tratamento"].value_counts()
    com = int(contagem.get("com_ia", 0))
    sem = int(contagem.get("sem_ia", 0))
    return f"N={len(df)} ({com} com_ia / {sem} sem_ia)"


def plot_tempo_por_tratamento(trials_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ1 — tempo até o green (s) por tratamento, escala log."""
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(6, 4.8))
    else:
        fig = ax.figure
    _boxplot_com_mediana(
        trials_df, "tempo_segundos", ax,
        titulo="RQ1 — Tempo até o green por tratamento",
        ylabel="Tempo (s, escala log)",
        escala_log=True,
    )
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/trials.csv — {_resumo_n(trials_df)}")
        fig.tight_layout()
    return fig


def plot_tempo_por_integrante(trials_df: pd.DataFrame) -> plt.Figure:
    """RQ1 — pequeno painel (facet) por integrante, mostrando variação individual."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
    for eixo, integrante in zip(axes, INTEGRANTES_ORDEM):
        sub = trials_df[trials_df["integrante"] == integrante]
        _boxplot_com_mediana(
            sub, "tempo_segundos", eixo,
            titulo=INTEGRANTES_ROTULOS.get(integrante, integrante),
            ylabel="Tempo (s, escala log)" if eixo is axes[0] else "",
            escala_log=True,
        )
    fig.suptitle("RQ1 — Tempo até o green por integrante e tratamento", fontweight="bold")
    _fonte(fig, f"Fonte: lab02/data/trials.csv — {_resumo_n(trials_df)}")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return fig


def plot_tempo_distribuicao(trials_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ1 — forma completa da distribuição do tempo (KDE + pontos individuais).

    Mediana/IQR resumem a distribuição em 3 números; com N pequeno (9/tratamento)
    isso pode esconder padrões (ex.: bimodalidade) que só aparecem olhando a
    distribuição inteira. O rug plot mostra cada trial individualmente por baixo
    da curva suavizada, então nenhuma observação fica escondida atrás do resumo.
    """
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(7, 4.8))
    else:
        fig = ax.figure
    df = trials_df.copy()
    df["log_tempo"] = np.log10(df["tempo_segundos"])
    for trat in ORDEM_TRATAMENTOS:
        sub = df[df["tratamento"] == trat]
        sns.kdeplot(
            x=sub["log_tempo"], ax=ax, color=PALETA[trat], fill=True, alpha=0.25,
            linewidth=2, label=ROTULOS_TRATAMENTO[trat], warn_singular=False,
        )
    sns.rugplot(data=df, x="log_tempo", hue="tratamento", palette=PALETA, ax=ax, height=0.06, legend=False)
    ticks_seg = [5, 10, 30, 60, 120, 300, 900]
    ax.set_xticks(np.log10(ticks_seg))
    ax.set_xticklabels([f"{t}s" if t < 60 else f"{t // 60}min" for t in ticks_seg])
    ax.set_xlabel("Tempo até o green (escala log)")
    ax.set_ylabel("Densidade")
    ax.set_title("RQ1 — Distribuição do tempo (KDE + pontos individuais)")
    ax.legend(frameon=False, title="Tratamento")
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/trials.csv — {_resumo_n(trials_df)}")
        fig.tight_layout()
    return fig


def plot_taxa_sucesso_por_tratamento(trials_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ2 — taxa de sucesso (testes passando / total) por tratamento."""
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(6, 4.8))
    else:
        fig = ax.figure
    _barplot_com_rotulo(
        trials_df, "taxa_sucesso", ax,
        titulo="RQ2 — Taxa de sucesso por tratamento",
        ylabel="Taxa de sucesso (mediana)",
        formato_percentual=True,
    )
    ax.text(
        0.5, -0.16, "Nenhuma falha registrada nos trials coletados (efeito teto)",
        transform=ax.transAxes, ha="center", fontsize=8, color="#52514e",
    )
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/trials.csv — {_resumo_n(trials_df)}")
        fig.tight_layout()
    return fig


def plot_testes_falhando_por_tratamento(trials_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ2 (complementar) — nº absoluto de testes falhando por tratamento."""
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(6, 4.8))
    else:
        fig = ax.figure
    _barplot_com_rotulo(
        trials_df, "testes_falhando", ax,
        titulo="RQ2 — Testes falhando ao final do time-box",
        ylabel="Testes falhando (mediana)",
    )
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/trials.csv — {_resumo_n(trials_df)}")
        fig.tight_layout()
    return fig


def plot_complexidade_por_tratamento(metricas_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ3 — complexidade ciclomática média (Radon) por tratamento."""
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(6, 4.8))
    else:
        fig = ax.figure
    _boxplot_com_mediana(
        metricas_df, "complexidade_media", ax,
        titulo="RQ3 — Complexidade ciclomática média",
        ylabel="Complexidade média (Radon cc)",
    )
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/static_metrics.csv — {_resumo_n(metricas_df)}")
        fig.tight_layout()
    return fig


def plot_loc_por_tratamento(metricas_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ3 (controle obrigatório) — LOC por tratamento."""
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(6, 4.8))
    else:
        fig = ax.figure
    _boxplot_com_mediana(
        metricas_df, "loc", ax,
        titulo="RQ3 — LOC (controle)",
        ylabel="Linhas de código (LOC)",
    )
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/static_metrics.csv — {_resumo_n(metricas_df)}")
        fig.tight_layout()
    return fig


def plot_mi_por_tratamento(metricas_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ3 (opcional) — Índice de Manutenibilidade por tratamento."""
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(6, 4.8))
    else:
        fig = ax.figure
    _boxplot_com_mediana(
        metricas_df, "mi", ax,
        titulo="RQ3 — Índice de Manutenibilidade (MI)",
        ylabel="MI (0-100)",
    )
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/static_metrics.csv — {_resumo_n(metricas_df)}")
        fig.tight_layout()
    return fig


def plot_complexidade_vs_loc(metricas_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ3 — dispersão complexidade x LOC, para checar se a diferença de
    complexidade não é só reflexo de mais linhas de código."""
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(6, 4.8))
    else:
        fig = ax.figure
    sns.scatterplot(
        data=metricas_df, x="loc", y="complexidade_media", hue="tratamento",
        hue_order=ORDEM_TRATAMENTOS, palette=PALETA, s=80, alpha=0.85, ax=ax,
    )
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles, [ROTULOS_TRATAMENTO[t] for t in ORDEM_TRATAMENTOS], title="Tratamento", frameon=False)
    ax.set_xlabel("LOC (controle)")
    ax.set_ylabel("Complexidade ciclomática média")
    ax.set_title("RQ3 — Complexidade vs. LOC")
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/static_metrics.csv — {_resumo_n(metricas_df)}")
        fig.tight_layout()
    return fig


def plot_correlacao_metricas_estruturais(metricas_df: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """RQ3 — matriz de correlação entre as métricas estruturais (LOC, complexidade, MI).

    Serve para checar multicolinearidade entre as métricas antes de discutir a
    RQ3 isoladamente por métrica: se LOC e complexidade estiverem fortemente
    correlacionadas, por exemplo, uma diferença de complexidade entre
    tratamentos pode ser só reflexo do tamanho do código (LOC), e não um
    efeito estrutural independente do assistente de IA.
    """
    proprio = ax is None
    if proprio:
        fig, ax = plt.subplots(figsize=(5.5, 4.8))
    else:
        fig = ax.figure
    colunas = {"loc": "LOC", "complexidade_media": "Complexidade", "mi": "MI"}
    corr = metricas_df[list(colunas)].corr().rename(index=colunas, columns=colunas)
    sns.heatmap(
        corr, ax=ax, annot=True, fmt=".2f", cmap=DIVERGENTE_CORRELACAO, vmin=-1, vmax=1,
        center=0, square=True, linewidths=1, linecolor="#fcfcfb",
        cbar_kws={"label": "Correlação de Pearson"},
    )
    ax.set_title("RQ3 — Correlação entre métricas estruturais")
    if proprio:
        _fonte(fig, f"Fonte: lab02/data/static_metrics.csv — {_resumo_n(metricas_df)}")
        fig.tight_layout()
    return fig


def montar_painel_geral(trials_df: pd.DataFrame, metricas_df: pd.DataFrame) -> plt.Figure:
    """Painel único (grid 2x4) combinando as visões principais de RQ1/RQ2/RQ3."""
    fig, axes = plt.subplots(2, 4, figsize=(22, 10))
    plot_tempo_por_tratamento(trials_df, ax=axes[0, 0])
    plot_tempo_distribuicao(trials_df, ax=axes[0, 1])
    plot_taxa_sucesso_por_tratamento(trials_df, ax=axes[0, 2])
    plot_complexidade_por_tratamento(metricas_df, ax=axes[0, 3])
    plot_loc_por_tratamento(metricas_df, ax=axes[1, 0])
    plot_mi_por_tratamento(metricas_df, ax=axes[1, 1])
    plot_complexidade_vs_loc(metricas_df, ax=axes[1, 2])
    plot_correlacao_metricas_estruturais(metricas_df, ax=axes[1, 3])
    fig.suptitle(
        "Lab02 — Assistente de IA vs. Codificação Manual (com_ia vs sem_ia)",
        fontsize=16, fontweight="bold",
    )
    _fonte(
        fig,
        f"Fontes: lab02/data/trials.csv ({_resumo_n(trials_df)}) · "
        f"lab02/data/static_metrics.csv ({_resumo_n(metricas_df)})",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    return fig


def gerar_resumo_markdown(resumos: dict[str, pd.DataFrame], n_trials: int, n_metricas: int) -> str:
    linhas = [
        "# Resumo estatístico — Lab02 (com_ia vs sem_ia)",
        "",
        f"- Trials (RQ1/RQ2): {n_trials}",
        f"- Trials com métricas estáticas (RQ3): {n_metricas}",
        "",
        "Mediana e IQR (Q3 - Q1) por tratamento. Métricas escolhidas por RQ em "
        "`docs/lab02/desenho-experimento.md`.",
        "",
    ]
    for nome_metrica, resumo in resumos.items():
        linhas.append(f"## {nome_metrica}")
        linhas.append("")
        linhas.append("| tratamento | n | média | mediana | q1 | q3 | iqr |")
        linhas.append("|---|---|---|---|---|---|---|")
        for _, row in resumo.iterrows():
            rotulo = ROTULOS_TRATAMENTO.get(row["tratamento"], row["tratamento"])
            linhas.append(
                f"| {rotulo} | {int(row['n'])} | {row['media']:.2f} | {row['mediana']:.2f} | "
                f"{row['q1']:.2f} | {row['q3']:.2f} | {row['iqr']:.2f} |"
            )
        linhas.append("")
        if "tempo_segundos" in nome_metrica:
            linhas.append(
                "> Note a média acima da mediana nos dois tratamentos (mais pronunciado "
                "no `com_ia`) — sinal de assimetria à direita, típica de métricas de "
                "tempo em Engenharia de Software (um ou dois trials mais lentos puxam a "
                "média para cima). É por isso que a RQ1 usa mediana + IQR como métrica "
                "primária, não a média (ver `docs/lab02/desenho-experimento.md`)."
            )
            linhas.append("")
    linhas.append(
        "**Nota (RQ2):** todos os trials coletados atingiram 100% dos testes de "
        "aceitação (`taxa_sucesso = 1.0`, `testes_falhando = 0`) — não houve "
        "variância de defeitos nesta amostra (efeito teto). A RQ2 fica limitada "
        "a essa constatação; uma amostra maior ou katas mais difíceis seriam "
        "necessários para observar diferença de defeitos entre tratamentos."
    )
    return "\n".join(linhas)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera o dashboard (RQ1/RQ2/RQ3) do Lab02 a partir de trials.csv e static_metrics.csv."
    )
    parser.add_argument("--trials-csv", type=Path, default=DEFAULT_TRIALS_CSV, help="CSV de trials (RQ1/RQ2)")
    parser.add_argument("--metricas-csv", type=Path, default=DEFAULT_METRICAS_CSV, help="CSV de métricas estáticas (RQ3)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Pasta de saída dos gráficos/resumo")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    trials_df = carregar_trials(args.trials_csv)
    metricas_df = carregar_metricas(args.metricas_csv)
    _, faltantes = mesclar_trials_e_metricas(trials_df, metricas_df)
    if not faltantes.empty:
        print(f"Aviso: {len(faltantes)} trial(s) sem par trial<->métrica (confira integrante/kata/tratamento):")
        print(faltantes[["integrante", "kata", "tratamento"]].to_string(index=False))

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    graficos = {
        "rq1_tempo.png": plot_tempo_por_tratamento(trials_df),
        "rq1_tempo_por_integrante.png": plot_tempo_por_integrante(trials_df),
        "rq1_distribuicao_tempo.png": plot_tempo_distribuicao(trials_df),
        "rq2_taxa_sucesso.png": plot_taxa_sucesso_por_tratamento(trials_df),
        "rq2_testes_falhando.png": plot_testes_falhando_por_tratamento(trials_df),
        "rq3_complexidade.png": plot_complexidade_por_tratamento(metricas_df),
        "rq3_loc.png": plot_loc_por_tratamento(metricas_df),
        "rq3_mi.png": plot_mi_por_tratamento(metricas_df),
        "rq3_complexidade_vs_loc.png": plot_complexidade_vs_loc(metricas_df),
        "rq3_correlacao_metricas.png": plot_correlacao_metricas_estruturais(metricas_df),
        "dashboard_geral.png": montar_painel_geral(trials_df, metricas_df),
    }
    for nome, fig in graficos.items():
        fig.savefig(out_dir / nome, dpi=150, bbox_inches="tight")
        plt.close(fig)

    resumos = {
        "tempo_segundos — RQ1 (s)": resumo_mediana_iqr(trials_df, "tempo_segundos"),
        "taxa_sucesso — RQ2": resumo_mediana_iqr(trials_df, "taxa_sucesso"),
        "testes_falhando — RQ2": resumo_mediana_iqr(trials_df, "testes_falhando"),
        "complexidade_media — RQ3": resumo_mediana_iqr(metricas_df, "complexidade_media"),
        "loc — RQ3 (controle)": resumo_mediana_iqr(metricas_df, "loc"),
        "mi — RQ3": resumo_mediana_iqr(metricas_df, "mi"),
    }
    resumo_md = gerar_resumo_markdown(resumos, n_trials=len(trials_df), n_metricas=len(metricas_df))
    (out_dir / "resumo_estatisticas.md").write_text(resumo_md, encoding="utf-8")

    print(f"Gráficos e resumo salvos em: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
