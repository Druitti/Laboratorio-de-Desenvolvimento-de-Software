"""Testes do script de métricas estáticas da Issue #14."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).with_name("static_metrics.py")
SPEC = importlib.util.spec_from_file_location("static_metrics", SCRIPT)
static_metrics = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(static_metrics)


def test_encontra_kata_existente():
    path = static_metrics.kata_path("k1_merge_intervals")
    assert path.name == "k1_merge_intervals"
    assert (path / "kata.py").is_file()


def test_rejeita_kata_inexistente():
    with pytest.raises(ValueError, match="Kata inexistente"):
        static_metrics.kata_path("kata_que_nao_existe")


def test_calcula_metricas_do_kata_incompleto():
    path = static_metrics.kata_path("k1_merge_intervals")
    metricas = static_metrics.compute_metrics(path / "kata.py", incluir_mi=False)

    assert metricas["loc"] > 0
    assert metricas["num_blocos"] == 1
    assert metricas["complexidade_media"] == 1.0
    assert metricas["complexidade_total"] == 1
    assert metricas["mi"] is None


def test_calcula_mi_quando_solicitado():
    path = static_metrics.kata_path("k1_merge_intervals")
    metricas = static_metrics.compute_metrics(path / "kata.py", incluir_mi=True)

    assert metricas["mi"] is not None
    assert 0.0 <= metricas["mi"] <= 100.0


def test_salva_csv_com_cabecalho_e_linha(tmp_path):
    output = tmp_path / "static_metrics.csv"
    row = {
        "data_hora_utc": "2026-09-10T12:00:00+00:00",
        "integrante": "Tavaresds1",
        "kata": "k1_merge_intervals",
        "tratamento": "sem_ia",
        "arquivo": "lab02/katas/k1_merge_intervals/kata.py",
        "loc": 16,
        "lloc": 5,
        "sloc": 3,
        "comentarios": 0,
        "linhas_em_branco": 5,
        "complexidade_media": "1.00",
        "complexidade_total": 1,
        "num_blocos": 1,
        "mi": "100.00",
    }

    static_metrics.save_csv(output, row)

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["kata"] == "k1_merge_intervals"
    assert rows[0]["complexidade_media"] == "1.00"


def _args(tmp_path, mi=False, tratamento="sem_ia"):
    return SimpleNamespace(
        kata="k1_merge_intervals",
        integrante="Tavaresds1",
        tratamento=tratamento,
        mi=mi,
        csv=tmp_path / "static_metrics.csv",
    )


def test_main_registra_linha_no_csv(monkeypatch, tmp_path):
    args = _args(tmp_path)
    monkeypatch.setattr(static_metrics, "parse_args", lambda: args)

    assert static_metrics.main() == 0

    with args.csv.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["integrante"] == "Tavaresds1"
    assert row["kata"] == "k1_merge_intervals"
    assert row["tratamento"] == "sem_ia"
    assert row["mi"] == ""


def test_main_rejeita_kata_inexistente(monkeypatch, tmp_path, capsys):
    args = _args(tmp_path)
    args.kata = "kata_que_nao_existe"
    monkeypatch.setattr(static_metrics, "parse_args", lambda: args)

    assert static_metrics.main() == 2
    assert not args.csv.exists()
    assert "Kata inexistente" in capsys.readouterr().err
