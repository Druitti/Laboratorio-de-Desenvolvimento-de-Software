"""Testes do script de cronometragem da Issue #13."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).with_name("timer_trial.py")
SPEC = importlib.util.spec_from_file_location("timer_trial", SCRIPT)
timer_trial = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(timer_trial)


def test_encontra_kata_existente():
    path = timer_trial.kata_path("k1_merge_intervals")
    assert path.name == "k1_merge_intervals"
    assert (path / "test_kata.py").is_file()


def test_rejeita_kata_inexistente():
    with pytest.raises(ValueError, match="Kata inexistente"):
        timer_trial.kata_path("kata_que_nao_existe")


def test_coleta_quantidade_de_testes():
    path = timer_trial.kata_path("k1_merge_intervals")
    assert timer_trial.collect_total(path) == 6


def test_executa_kata_incompleto_sem_confundir_com_green():
    path = timer_trial.kata_path("k1_merge_intervals")
    passed, returncode, output = timer_trial.run_tests(path, total=6)
    assert passed == 0
    assert returncode != 0
    assert "failed" in output


def test_salva_csv_com_cabecalho_e_linha(tmp_path):
    output = tmp_path / "trials.csv"
    row = {
        "data_hora_utc": "2026-09-10T12:00:00+00:00",
        "integrante": "gabsant07",
        "kata": "k1_merge_intervals",
        "tratamento": "sem_ia",
        "tempo_segundos": "2100.00",
        "tempo_minutos": "35.00",
        "censurado": "sim",
        "testes_passando": 4,
        "testes_total": 6,
        "testes_falhando": 2,
        "taxa_sucesso": "0.6667",
    }

    timer_trial.save_csv(output, row)

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["integrante"] == "gabsant07"
    assert rows[0]["censurado"] == "sim"
    assert rows[0]["testes_falhando"] == "2"


def _args(tmp_path, limit=35.0):
    return SimpleNamespace(
        integrante="gabsant07",
        kata="k1_merge_intervals",
        tratamento="sem_ia",
        csv=tmp_path / "trials.csv",
        intervalo=0.01,
        limite_minutos=limit,
    )


def test_main_registra_green(monkeypatch, tmp_path):
    args = _args(tmp_path)
    monkeypatch.setattr(timer_trial, "parse_args", lambda: args)
    monkeypatch.setattr(timer_trial, "collect_total", lambda _path: 6)
    monkeypatch.setattr(timer_trial, "run_tests", lambda _path, _total: (6, 0, "6 passed"))
    times = iter([100.0, 112.0, 112.0])
    monkeypatch.setattr(timer_trial.time, "monotonic", lambda: next(times))

    assert timer_trial.main() == 0

    with args.csv.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["censurado"] == "nao"
    assert row["tempo_segundos"] == "12.00"
    assert row["taxa_sucesso"] == "1.0000"


def test_main_registra_censura_no_limite(monkeypatch, tmp_path):
    args = _args(tmp_path, limit=0.01)
    monkeypatch.setattr(timer_trial, "parse_args", lambda: args)
    monkeypatch.setattr(timer_trial, "collect_total", lambda _path: 6)
    monkeypatch.setattr(timer_trial, "run_tests", lambda _path, _total: (4, 1, "2 failed, 4 passed"))
    times = iter([20.0, 20.6, 20.6])
    monkeypatch.setattr(timer_trial.time, "monotonic", lambda: next(times))

    assert timer_trial.main() == 0

    with args.csv.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["censurado"] == "sim"
    assert row["tempo_segundos"] == "0.60"
    assert row["testes_passando"] == "4"
    assert row["testes_falhando"] == "2"


def test_ctrl_c_cancela_sem_gravar_csv(monkeypatch, tmp_path):
    args = _args(tmp_path)
    monkeypatch.setattr(timer_trial, "parse_args", lambda: args)
    monkeypatch.setattr(timer_trial, "collect_total", lambda _path: 6)
    monkeypatch.setattr(
        timer_trial,
        "run_tests",
        lambda _path, _total: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr(timer_trial.time, "monotonic", lambda: 10.0)

    assert timer_trial.main() == 130
    assert not args.csv.exists()
