import csv
import json
import random
import sqlite3

import pytest

from lab05.pilot import COLUMNS, JOURNAL_MODES, WORKLOADS, main, percentile_ms, run_once, run_pilot, summarize

SMALL = {"write_transactions": 20, "read_rows": 50, "read_queries": 30}


@pytest.mark.parametrize("mode", JOURNAL_MODES)
@pytest.mark.parametrize("workload", WORKLOADS)
def test_run_once_applies_the_journal_mode_and_counts_operations(tmp_path, mode, workload):
    result = run_once(mode, workload, tmp_path, rng=random.Random(1), **SMALL)
    expected = SMALL["write_transactions"] if workload == "write" else SMALL["read_queries"]
    assert result["operations"] == expected
    assert result["ops_per_second"] > 0
    assert 0 < result["p50_ms"] <= result["p95_ms"] <= result["p99_ms"] <= result["max_ms"]
    database = tmp_path / f"{mode}-{workload}.db"
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == mode
        rows = connection.execute("SELECT count(*) FROM t").fetchone()[0]
    assert rows == (SMALL["write_transactions"] if workload == "write" else SMALL["read_rows"])


def test_invalid_condition_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        run_once("memory", "write", tmp_path, rng=random.Random(1), **SMALL)


def test_each_round_runs_the_four_conditions_in_a_seeded_random_order(tmp_path):
    rows = run_pilot(rounds=3, seed=9, base_dir=tmp_path, **SMALL)
    assert len(rows) == 12
    orders = []
    for round_number in (1, 2, 3):
        cells = [(r["journal_mode"], r["workload"]) for r in rows if r["round"] == round_number]
        assert sorted(cells) == sorted((m, w) for m in JOURNAL_MODES for w in WORKLOADS)
        orders.append(cells)
    again = run_pilot(rounds=3, seed=9, base_dir=tmp_path, **SMALL)
    assert [(r["journal_mode"], r["workload"]) for r in again] == [c for cells in orders for c in cells]
    assert list(tmp_path.iterdir()) == []


def test_percentile_uses_the_inclusive_method():
    values = list(range(1, 101))
    assert percentile_ms([v * 1_000_000 for v in values], 50) == pytest.approx(50.5)
    assert percentile_ms([v * 1_000_000 for v in values], 95) == pytest.approx(95.05)


def test_summary_has_one_line_per_condition(tmp_path):
    summary = summarize(run_pilot(rounds=2, seed=1, base_dir=tmp_path, **SMALL))
    assert len(summary) == 4
    assert all(item["runs"] == 2 and item["cv"] >= 0 for item in summary)


def test_cli_writes_csv_and_environment(tmp_path):
    output, env = tmp_path / "pilot.csv", tmp_path / "env.json"
    assert main(["--rounds", "1", "--write-transactions", "10", "--read-rows", "20", "--read-queries", "10",
                 "--output", str(output), "--env", str(env)]) == 0
    with output.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == COLUMNS
        assert len(list(reader)) == 4
    data = json.loads(env.read_text(encoding="utf-8"))
    assert data["sqlite_version"] == sqlite3.sqlite_version
    assert data["pragmas"]["synchronous"] == "FULL"
