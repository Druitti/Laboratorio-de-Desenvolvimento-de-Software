import csv

import pytest

from lab04.real_data import (
    COLUMNS,
    DEFAULT_INPUT,
    GROUPS,
    WITH_BOT,
    WITHOUT_BOT,
    load_real_data,
    main,
    read_config,
    summarize,
)
from lab04.simulation import read_real_samples, simulate_groups

CONFIG = {**read_config(), "n_per_group": 2, "review_bots": ["coderabbitai"]}


def make_row(index, group):
    hours = index + 1
    return {
        "group": group,
        "value": f"{hours:.4f}",
        "repository": f"o/r{index}",
        "pr_number": 10,
        "source_url": f"https://github.com/o/r{index}/pull/10",
        "created_at": "2026-02-01T00:00:00Z",
        "merged_at": f"2026-02-01T{hours:02d}:00:00Z",
        "review_bots": "coderabbitai" if group == WITH_BOT else "",
        "additions": 1,
        "deletions": 1,
        "changed_files": 1,
        "collected_at": "2026-11-05T00:00:00Z",
        "source": "GitHub GraphQL API",
        "method": "sorteio",
        "limitations": "observacional",
    }


def write_rows(path, rows, columns=COLUMNS):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def valid_rows():
    return [make_row(0, WITH_BOT), make_row(1, WITH_BOT), make_row(2, WITHOUT_BOT), make_row(3, WITHOUT_BOT)]


def test_valid_file_is_loaded_with_types(tmp_path):
    rows = load_real_data(write_rows(tmp_path / "real.csv", valid_rows()), CONFIG)
    assert [row["value"] for row in rows] == [1.0, 2.0, 3.0, 4.0]
    assert rows[0]["review_bots"] == ["coderabbitai"]
    assert rows[2]["review_bots"] == []


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"group": "outro"}, "desconhecido"),
        ({"value": "0"}, "positivo"),
        ({"value": "abc"}, "inválido"),
        ({"value": "1.5000"}, "difere"),
        ({"value": "0.1000", "merged_at": "2026-02-01T00:06:00Z"}, "exposição"),
        ({"source": ""}, "vazia"),
        ({"limitations": " "}, "vazia"),
        ({"created_at": "2025-12-31T23:00:00Z", "merged_at": "2026-01-01T00:00:00Z"}, "fora da janela"),
        ({"created_at": "2026-02-01T00:00:00", "merged_at": "2026-02-01T01:00:00"}, "timezone"),
        ({"created_at": "2026-10-31T23:00:00Z", "merged_at": "2026-11-01T00:00:00Z"}, "fora da janela"),
        ({"source_url": "https://github.com/o/outro/pull/10"}, "source_url"),
        ({"review_bots": ""}, "sem bot"),
        ({"review_bots": "desconhecido"}, "fora da lista"),
    ],
)
def test_invalid_row_is_rejected(tmp_path, changes, message):
    rows = valid_rows()
    rows[0].update(changes)
    with pytest.raises(ValueError, match=message):
        load_real_data(write_rows(tmp_path / "real.csv", rows), CONFIG)


def test_without_group_cannot_register_a_bot(tmp_path):
    rows = valid_rows()
    rows[2]["review_bots"] = "coderabbitai"
    with pytest.raises(ValueError, match="registra bot"):
        load_real_data(write_rows(tmp_path / "real.csv", rows), CONFIG)


def test_merge_after_collection_cutoff_is_rejected(tmp_path):
    rows = valid_rows()
    rows[0].update(created_at="2026-06-30T23:00:00Z", merged_at="2026-11-01T00:00:00Z", value="2953.0000")
    with pytest.raises(ValueError, match="corte"):
        load_real_data(write_rows(tmp_path / "real.csv", rows), CONFIG)


def test_missing_column_group_size_and_repeated_repository_are_rejected(tmp_path):
    path = tmp_path / "real.csv"
    with pytest.raises(ValueError, match="Colunas ausentes.*limitations"):
        load_real_data(write_rows(path, valid_rows(), [c for c in COLUMNS if c != "limitations"]), CONFIG)

    with pytest.raises(ValueError, match="esperado 2"):
        load_real_data(write_rows(path, valid_rows()[:3]), CONFIG)

    rows = valid_rows()
    rows[1].update(repository="o/r0", source_url="https://github.com/o/r0/pull/10")
    with pytest.raises(ValueError, match="mais de uma observação"):
        load_real_data(write_rows(path, rows), CONFIG)


def test_config_rejects_inverted_dates(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        '{"window_start": "2026-07-01T00:00:00Z", "window_end": "2026-01-01T00:00:00Z",'
        ' "merged_before": "2026-11-01T00:00:00Z", "frame_size": 500, "min_minutes_to_merge": 10,'
        ' "max_prs_per_repository": 100, "min_prs_per_group": 5,'
        ' "n_per_group": 30, "seed": 42, "review_bots": ["x"]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="window_start"):
        read_config(path)


def test_committed_sample_is_valid_and_feeds_the_simulation():
    rows = load_real_data(DEFAULT_INPUT, read_config())
    assert len(rows) == 60

    summary = summarize(rows)
    for group in GROUPS:
        assert summary["groups"][group]["n"] == 30
    assert summary["between_groups"]["variance_ratio_max_min"] >= 1

    samples = read_real_samples(DEFAULT_INPUT)
    assert {group: len(values) for group, values in samples.items()} == {WITH_BOT: 30, WITHOUT_BOT: 30}
    simulated = simulate_groups(samples, n_per_group=30, seed=42)
    assert set(simulated) == set(GROUPS)


def test_cli_reports_invalid_file_without_traceback(tmp_path, capsys):
    path = write_rows(tmp_path / "real.csv", valid_rows()[:3])
    assert main(["--input", str(path), "--summary", str(tmp_path / "s.json")]) == 1
    assert "Dados inválidos" in capsys.readouterr().err
    assert not (tmp_path / "s.json").exists()


def test_real_groups_report_statistic_p_value_and_effect_size():
    from scipy import stats

    from lab04.real_data import analyze_real_groups

    samples = {"a": [1.0, 2.0, 3.0, 4.0, 10.0], "b": [2.0, 4.0, 6.0, 8.0, 30.0]}
    result = analyze_real_groups(samples)
    welch = stats.ttest_ind(samples["a"], samples["b"], equal_var=False)
    assert result["groups"] == ["a", "b"]
    assert result["welch"]["statistic"] == pytest.approx(welch.statistic)
    assert result["welch"]["df"] == pytest.approx(welch.df)
    low, high = welch.confidence_interval(0.95)
    assert result["welch"]["ci_hours"] == pytest.approx([low, high])
    assert result["welch"]["mean_difference_hours"] == pytest.approx(-6.0)
    u = stats.mannwhitneyu(samples["a"], samples["b"], alternative="two-sided").statistic
    assert result["mann_whitney"]["probability_of_superiority"] == pytest.approx(u / 25)
    assert result["mann_whitney"]["rank_biserial"] == pytest.approx(2 * u / 25 - 1)
    assert result["mann_whitney"]["hodges_lehmann_hours"] == pytest.approx(-3.0)  # mediana das 25 diferenças
    for test in ("welch", "mann_whitney"):
        assert "H0" in result[test]["conclusion"]


def test_real_sample_analysis_runs_on_the_committed_csv():
    from lab04.real_data import analyze_real_groups

    result = analyze_real_groups(read_real_samples(DEFAULT_INPUT))
    assert result["groups"] == [WITH_BOT, WITHOUT_BOT]
    assert 0 <= result["welch"]["p_value"] <= 1
    assert -1 <= result["mann_whitney"]["rank_biserial"] <= 1
