import random
import sqlite3

import pytest

from lab05.pilot import run_once
from lab05.validation import call_overhead_ms, order_effects, run_checks, spearman, summarize

SMALL = {"write_transactions": 10, "read_rows": 40, "read_queries": 20}


def test_spearman_handles_monotone_relations_and_ties():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 1, 2, 2], [5, 5, 6, 6]) == pytest.approx(1.0)
    assert spearman([1, 2, 3], [7, 7, 7]) == 0.0


def test_fullfsync_and_single_transaction_options_reach_sqlite(tmp_path):
    run_once("wal", "write", tmp_path, rng=random.Random(1), fullfsync=True, **SMALL)
    result = run_once("delete", "read", tmp_path, rng=random.Random(1), single_transaction=True, **SMALL)
    assert result["operations"] == SMALL["read_queries"]
    with sqlite3.connect(tmp_path / "wal-write.db") as connection:
        assert connection.execute("SELECT count(*) FROM t").fetchone()[0] == SMALL["write_transactions"]


def test_checks_cover_every_variant_and_mode_in_each_round(tmp_path):
    rows = run_checks(rounds=2, seed=3, base_dir=tmp_path, **SMALL)
    assert len(rows) == 16
    cells = {(r["check"], r["variant"], r["journal_mode"]) for r in rows if r["round"] == 1}
    assert len(cells) == 8
    summary = summarize(rows)
    assert set(summary["read_transaction"]) == {"per_query", "single"}
    assert set(summary["fullfsync"]) == {"off", "on"}
    assert all(item["wal_over_delete"] > 0 for check in summary.values() for item in check.values())
    assert list(tmp_path.iterdir()) == []


def test_call_overhead_is_positive():
    overhead = call_overhead_ms(calls=200)
    assert 0 < overhead["p50_ms"] <= overhead["p95_ms"]


def test_order_effects_use_the_pilot_columns():
    rows = [
        {"workload": w, "journal_mode": m, "order_in_round": str(p), "round": str(r), "ops_per_second": str(10 * p)}
        for w in ("write", "read") for m in ("delete", "wal") for r, p in ((1, 1), (2, 2), (3, 3))
    ]
    effects = order_effects(rows)
    assert len(effects) == 4
    assert all(e["rho_position"] == pytest.approx(1.0) and e["runs"] == 3 for e in effects)
