"""Offline synthetic replication comparisons; no empirical results."""
import csv
import hashlib
import json

import pytest

from lab03 import replication as r


def write(path, rows, columns=None):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def population():
    return [dict(repository=f'owner/repo{i}', metric='10', dora_class='High',
                 window_start='2025-01-01T00:00:00Z', window_end='2026-01-01T00:00:00Z',
                 collected_at='2026-10-22T12:00:00Z') for i in range(30)]


def inputs(tmp_path):
    return write(tmp_path/'original.csv', population()), write(tmp_path/'replicated.csv', population())


def test_differences_zero_missing_classes_temporal_and_hashes(tmp_path):
    original, replicated = population(), population()
    replicated[0]['repository'] = 'OWNER/REPO0'
    replicated[0]['metric'] = '15'
    original[1]['metric'], replicated[1]['metric'] = '0', '1'
    original[2]['metric'], replicated[2]['metric'] = '0', '0'
    replicated[3]['metric'] = ''
    original[4]['metric'], replicated[4]['metric'] = '-10', '-5'
    replicated[5]['dora_class'] = '4'
    replicated[6]['dora_class'] = ''
    replicated[7]['collected_at'] = '2026-10-23T12:00:00Z'
    replicated[8]['window_start'] = '2024-01-01T00:00:00Z'
    a, b = write(tmp_path/'a.csv', original), write(tmp_path/'b.csv', replicated)
    report = r.compare(a, b, tmp_path/'out', ['metric'], command=['python', '-m', 'lab03.replication'])
    rows = {row['repository'].casefold(): row for row in r.read_table(tmp_path/'out/comparison.csv', r.FIELDS).values()}
    assert float(rows['owner/repo0']['relative_difference']) == .5
    assert float(rows['owner/repo0']['absolute_difference']) == 5
    assert rows['owner/repo1']['status'] == 'zero_baseline'
    assert rows['owner/repo1']['relative_difference'] == ''
    assert rows['owner/repo2']['relative_difference'] == '0.0'
    assert rows['owner/repo3']['status'] == 'missing_replicated'
    assert float(rows['owner/repo4']['relative_difference']) == .5
    assert report['same_class_repositories'] == 28 and report['class_pairs'] == 29
    assert report['same_class_percent'] == pytest.approx(100*28/29)
    assert rows['owner/repo7']['collection_status'] == 'different'
    assert rows['owner/repo8']['window_status'] == 'different'
    assert report['input_sha256']['original'] == hashlib.sha256(a.read_bytes()).hexdigest()
    assert json.loads((tmp_path/'out/summary.json').read_text(encoding='utf-8')) == report
    assert '28/29' in (tmp_path/'out/summary.md').read_text(encoding='utf-8')
    with pytest.raises(ValueError, match='Saída já existe'):
        r.compare(a, b, tmp_path/'out', ['metric'])


def test_explicit_selection_missing_repositories_and_no_class_denominator(tmp_path):
    selected = population()
    a = write(tmp_path/'a.csv', [{**row, 'dora_class': ''} for row in population()[1:]])
    b = write(tmp_path/'b.csv', [{**row, 'dora_class': ''} for row in population()[:-1]])
    selection = write(tmp_path/'selection.csv', [{'repository': row['repository']} for row in selected])
    report = r.compare(a, b, tmp_path/'out', ['metric'], selection_path=selection)
    assert report['class_pairs'] == 0 and report['same_class_percent'] is None
    assert report['metric_statuses']['metric'] == {'missing_original': 1, 'missing_replicated': 1, 'ok': 28}
    audit = {row['repository']: row for row in report['repository_audit']}
    assert not audit['owner/repo0']['original_present']
    assert not audit['owner/repo29']['replicated_present']


@pytest.mark.parametrize('bad', ['nan', 'inf', '-inf', 'not numeric', '1e309'])
def test_reject_nonfinite_and_invalid_numbers(tmp_path, bad):
    a, b = inputs(tmp_path)
    rows = population()
    rows[0]['metric'] = bad
    write(b, rows)
    with pytest.raises(ValueError, match='Número'):
        r.compare(a, b, tmp_path/'out', ['metric'])
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('change', ['duplicate', 'identity', 'class', 'count', 'columns', 'headers'])
def test_reject_bad_identity_schema_and_sample(tmp_path, change):
    a, b = inputs(tmp_path)
    rows = population()
    if change == 'duplicate': rows[-1]['repository'] = rows[0]['repository'].upper()
    if change == 'identity': rows[0]['repository'] = 'https://github.com/o/r'
    if change == 'class': rows[0]['dora_class'] = '5'
    if change == 'count': rows.pop()
    if change == 'columns':
        for row in rows: del row['metric']
    write(b, rows)
    if change == 'headers': b.write_text('repository,metric,metric,dora_class\no/r,1,2,High\n')
    with pytest.raises(ValueError):
        r.compare(a, b, tmp_path/'out', ['metric'])
    assert not (tmp_path/'out').exists()


def test_cli_mapping_and_command_audit(tmp_path):
    rows = [{('repo' if k == 'repository' else 'C1' if k == 'dora_class' else k): v for k, v in row.items()}
            for row in population()]
    a, b = write(tmp_path/'a.csv', rows), write(tmp_path/'b.csv', rows)
    r.main(['--original', str(a), '--replicated', str(b), '--metrics', 'metric',
            '--repository-column', 'repo', '--class-column', 'C1', '--out', str(tmp_path/'out')])
    report = json.loads((tmp_path/'out/summary.json').read_text(encoding='utf-8'))
    assert report['same_class_percent'] == 100
    assert '--repository-column' in report['command_argv']


def test_reordered_rows_numeric_classes_and_multiple_metrics(tmp_path):
    original, replicated = population(), list(reversed(population()))
    for row in original:
        row['second'] = '2'
        row['dora_class'] = '3.0'
    for row in replicated:
        row['second'] = '1'
    a, b = write(tmp_path/'a.csv', original), write(tmp_path/'b.csv', replicated)
    report = r.compare(a, b, tmp_path/'out', ['metric', 'second'])
    assert report['same_class_percent'] == 100
    with (tmp_path/'out/comparison.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 60
    assert {row['relative_difference'] for row in rows if row['metric'] == 'second'} == {'-0.5'}


@pytest.mark.parametrize('value', ['1.5', 'nan', 'inf'])
def test_nonintegral_or_nonfinite_class_rejected(value):
    with pytest.raises(ValueError, match='Classe DORA'):
        r.dora(value, 'synthetic')


def test_overflow_difference_and_input_changed(tmp_path, monkeypatch):
    a, b = inputs(tmp_path)
    left, right = population(), population()
    left[0]['metric'], right[0]['metric'] = '-1e308', '1e308'
    write(a, left); write(b, right)
    with pytest.raises(ValueError, match='Diferença não finita'):
        r.compare(a, b, tmp_path/'out', ['metric'])
    a, b = inputs(tmp_path)
    original_read = r.read_table

    def mutate_after_read(path, *args):
        result = original_read(path, *args)
        if path == b:
            b.write_bytes(b.read_bytes() + b'\n')
        return result

    monkeypatch.setattr(r, 'read_table', mutate_after_read)
    with pytest.raises(ValueError, match='mudou'):
        r.compare(a, b, tmp_path/'out', ['metric'])
