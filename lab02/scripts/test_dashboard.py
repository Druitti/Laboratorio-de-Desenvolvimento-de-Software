"""Testes do script do dashboard da Issue #16."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.figure
import pandas as pd
import pytest


SCRIPT = Path(__file__).with_name("dashboard.py")
SPEC = importlib.util.spec_from_file_location("dashboard", SCRIPT)
dashboard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(dashboard)


def _trials_df() -> pd.DataFrame:
    return pd.DataFrame({
        "integrante": ["a", "a", "b", "b"],
        "kata": ["k1", "k2", "k1", "k2"],
        "tratamento": ["com_ia", "sem_ia", "com_ia", "sem_ia"],
        "tempo_segundos": [10.0, 100.0, 20.0, 200.0],
        "taxa_sucesso": [1.0, 1.0, 1.0, 1.0],
        "testes_falhando": [0, 0, 0, 0],
    })


def _metricas_df() -> pd.DataFrame:
    return pd.DataFrame({
        "integrante": ["a", "a", "b", "b"],
        "kata": ["k1", "k2", "k1", "k2"],
        "tratamento": ["com_ia", "sem_ia", "com_ia", "sem_ia"],
        "loc": [10, 20, 12, 22],
        "complexidade_media": [3.0, 5.0, 4.0, 6.0],
        "mi": [90.0, 70.0, 85.0, 65.0],
    })


def test_resumo_mediana_iqr_calcula_valores_esperados():
    df = pd.DataFrame({
        "tratamento": ["sem_ia", "sem_ia", "sem_ia", "sem_ia", "com_ia", "com_ia", "com_ia", "com_ia"],
        "valor": [10, 20, 30, 40, 1, 2, 3, 4],
    })
    resumo = dashboard.resumo_mediana_iqr(df, "valor")

    sem_ia = resumo.set_index("tratamento").loc["sem_ia"]
    assert sem_ia["n"] == 4
    assert sem_ia["media"] == 25.0
    assert sem_ia["mediana"] == 25.0
    assert sem_ia["q1"] == 17.5
    assert sem_ia["q3"] == 32.5
    assert sem_ia["iqr"] == pytest.approx(15.0)


def test_resumo_mediana_iqr_inclui_media_para_contraste_com_mediana():
    """A média deve ser reportada ao lado da mediana para evidenciar assimetria
    (métricas de software costumam ter média >> mediana — ver desenho do experimento)."""
    df = pd.DataFrame({
        "tratamento": ["sem_ia", "sem_ia", "sem_ia", "sem_ia"],
        "valor": [1, 2, 3, 100],
    })
    resumo = dashboard.resumo_mediana_iqr(df, "valor")

    sem_ia = resumo.set_index("tratamento").loc["sem_ia"]
    assert sem_ia["media"] == pytest.approx(26.5)
    assert sem_ia["mediana"] == 2.5
    assert sem_ia["media"] > sem_ia["mediana"]


def test_resumo_mediana_iqr_mantem_ordem_fixa():
    df = pd.DataFrame({
        "tratamento": ["com_ia", "sem_ia", "com_ia", "sem_ia"],
        "valor": [1, 2, 3, 4],
    })
    resumo = dashboard.resumo_mediana_iqr(df, "valor")

    assert list(resumo["tratamento"]) == ["sem_ia", "com_ia"]


def test_mesclar_trials_e_metricas_junta_por_chave():
    trials = _trials_df()
    metricas = _metricas_df()

    completos, faltantes = dashboard.mesclar_trials_e_metricas(trials, metricas)

    assert len(completos) == 4
    assert faltantes.empty


def test_mesclar_trials_e_metricas_sinaliza_trial_sem_metrica():
    trials = _trials_df()
    metricas = _metricas_df().iloc[:-1]  # remove o par (b, k2, sem_ia)

    completos, faltantes = dashboard.mesclar_trials_e_metricas(trials, metricas)

    assert len(completos) == 3
    assert len(faltantes) == 1
    linha = faltantes.iloc[0]
    assert (linha["integrante"], linha["kata"], linha["tratamento"]) == ("b", "k2", "sem_ia")


@pytest.mark.parametrize("funcao,df_builder", [
    (dashboard.plot_tempo_por_tratamento, _trials_df),
    (dashboard.plot_tempo_distribuicao, _trials_df),
    (dashboard.plot_taxa_sucesso_por_tratamento, _trials_df),
    (dashboard.plot_testes_falhando_por_tratamento, _trials_df),
    (dashboard.plot_complexidade_por_tratamento, _metricas_df),
    (dashboard.plot_loc_por_tratamento, _metricas_df),
    (dashboard.plot_mi_por_tratamento, _metricas_df),
    (dashboard.plot_complexidade_vs_loc, _metricas_df),
    (dashboard.plot_correlacao_metricas_estruturais, _metricas_df),
])
def test_funcoes_de_plot_retornam_figure(funcao, df_builder):
    fig = funcao(df_builder())
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


def test_plot_tempo_por_integrante_retorna_figure():
    df = pd.DataFrame({
        "integrante": ["Druitti", "gabsant07", "tavares"],
        "kata": ["k1", "k1", "k1"],
        "tratamento": ["com_ia", "sem_ia", "com_ia"],
        "tempo_segundos": [10.0, 100.0, 20.0],
    })
    fig = dashboard.plot_tempo_por_integrante(df)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


def test_montar_painel_geral_retorna_figure():
    fig = dashboard.montar_painel_geral(_trials_df(), _metricas_df())
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


def test_gerar_resumo_markdown_contem_metricas_e_nota_rq2():
    resumos = {
        "tempo_segundos — RQ1 (s)": dashboard.resumo_mediana_iqr(_trials_df(), "tempo_segundos"),
    }
    texto = dashboard.gerar_resumo_markdown(resumos, n_trials=4, n_metricas=4)

    assert "tempo_segundos — RQ1 (s)" in texto
    assert "Sem IA" in texto and "Com IA" in texto
    assert "média" in texto
    assert "assimetria" in texto
    assert "efeito teto" in texto


def test_main_gera_arquivos(tmp_path):
    trials_csv = tmp_path / "trials.csv"
    metricas_csv = tmp_path / "static_metrics.csv"
    out_dir = tmp_path / "saida"

    trials_df = _trials_df().assign(
        data_hora_utc="2026-01-01T00:00:00+00:00",
        tempo_minutos=lambda d: d["tempo_segundos"] / 60,
        censurado="nao",
        testes_passando=5,
        testes_total=5,
    )
    metricas_df = _metricas_df().assign(
        data_hora_utc="2026-01-01T00:00:00+00:00",
        arquivo="lab02/katas/k1/kata.py",
        lloc=10, sloc=8, comentarios=0, linhas_em_branco=1,
        complexidade_total=lambda d: d["complexidade_media"],
        num_blocos=1,
    )
    trials_df.to_csv(trials_csv, index=False)
    metricas_df.to_csv(metricas_csv, index=False)

    codigo = dashboard.main([
        "--trials-csv", str(trials_csv),
        "--metricas-csv", str(metricas_csv),
        "--out-dir", str(out_dir),
    ])

    assert codigo == 0
    assert (out_dir / "dashboard_geral.png").is_file()
    assert (out_dir / "rq1_tempo.png").is_file()
    assert (out_dir / "rq3_correlacao_metricas.png").is_file()
    assert (out_dir / "resumo_estatisticas.md").is_file()
