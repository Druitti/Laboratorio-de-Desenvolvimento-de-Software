"""Valida que os testes de aceitação passam contra o gabarito (só para o grupo)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
REF = ROOT / "solutions.py"


def _load_ref():
    spec = importlib.util.spec_from_file_location("ref_solutions", REF)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


ref = _load_ref()


def test_k1():
    assert ref.merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [
        [1, 6],
        [8, 10],
        [15, 18],
    ]
    assert ref.merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]
    assert ref.merge_intervals([]) == []
    assert ref.merge_intervals([[8, 10], [1, 3], [2, 6]]) == [[1, 6], [8, 10]]


def test_k2():
    assert ref.flatten_dict({"a": 1, "b": {"c": 2, "d": {"e": 3}}}) == {
        "a": 1,
        "b.c": 2,
        "b.d.e": 3,
    }
    assert ref.flatten_dict({"a": {"b": 1}}, sep="_") == {"a_b": 1}


def test_k3():
    lines = [
        "2026-09-09 14:03:11 ERROR disco cheio",
        "2026-09-09 14:10:00 INFO ok",
        "2026-09-09 15:01:00 FATAL crash",
        "2026-09-09 15:02:00 ERROR x",
    ]
    assert ref.errors_by_hour(lines) == {"14": 1, "15": 2}


def test_k4():
    assert ref.longest_free_streak([1, 0, 0, 1, 0, 0, 0, 1]) == 3
    assert ref.longest_free_streak([]) == 0


def test_k5():
    assert ref.is_valid_code("12345674") is True
    assert ref.is_valid_code("12345670") is False
    assert ref.is_valid_code("00000000") is True


def test_k6():
    assert ref.frame_score([3, 5, 2]) == 10
    assert ref.frame_score([10, 3, 4]) == 24
    assert ref.frame_score([10, 10, 5]) == 45
