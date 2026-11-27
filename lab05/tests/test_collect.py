import csv
import json
import sqlite3

import pytest

from lab05.collect import main, validate_csv
from lab05.pilot import COLUMNS


PARAMETERS = dict(rounds=2, seed=5, write_transactions=1, read_rows=5, read_queries=1)


@pytest.fixture
def collection(tmp_path):
    output = tmp_path / "collection"
    args = [arg for key, value in PARAMETERS.items() for arg in (f"--{key.replace('_', '-')}", str(value))]
    assert main(["--output-dir", str(output), "--warmup-rounds", "2", *args]) == 0
    return output


def test_collection_publishes_validated_pilot_schema_after_warmup(collection):
    path = collection / "collection.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == COLUMNS
        rows = list(reader)
    assert [row["run_id"] for row in rows] == [str(i) for i in range(1, 9)]
    assert validate_csv(path, **PARAMETERS) == 8
    metadata = json.loads((collection / "environment.json").read_text(encoding="utf-8"))
    assert metadata["validated_rows"] == 8
    assert metadata["warmup_rounds"] == 2
    assert metadata["sqlite_version"] == sqlite3.sqlite_version
    assert metadata["pragmas"] == {
        "journal_mode": ["delete", "wal"], "synchronous": "FULL", "page_size": 4096, "fullfsync": 0,
    }


@pytest.mark.parametrize(
    ("column", "value", "error"),
    [
        ("order_in_round", "2", "ordem"),
        ("operations", "99", "carga"),
        ("ops_per_second", "nan", "incoerentes"),
        ("p99_ms", "0", "incoerentes"),
    ],
)
def test_validator_rejects_invalid_csv(collection, column, value, error):
    path = collection / "collection.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0][column] = value
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match=error):
        validate_csv(path, **PARAMETERS)


def test_wrong_sqlite_version_aborts_before_collecting(tmp_path):
    output = tmp_path / "collection"
    with pytest.raises(SystemExit) as exc:
        main(["--output-dir", str(output), "--require-sqlite", "0.0.0"])
    assert exc.value.code == 2
    assert not output.exists()
