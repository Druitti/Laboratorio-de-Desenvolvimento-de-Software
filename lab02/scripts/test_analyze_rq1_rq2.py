import csv
from pathlib import Path

import pytest

from analyze_rq1_rq2 import analyze, paired_test, read_trials

SOURCE = Path(__file__).resolve().parents[1] / 'data/trials.csv'


def test_repository_results_and_order_independence():
    rows = read_trials(SOURCE)
    summary, pairs, tests = analyze(rows)
    assert analyze(list(reversed(rows))) == (summary, pairs, tests)
    assert tests['tempo_segundos']['p_valor'] == 0.125
    assert tests['tempo_segundos']['estatistica'] == 0
    assert tests['tempo_segundos']['n_pares'] == 3
    assert tests['taxa_sucesso']['status'] == 'sem_variacao'
    assert tests['taxa_sucesso']['p_valor'] is None


def test_direction_and_tied_ranks():
    assert paired_test([-1, -1, -1], 'less')['p_valor'] == 0.125
    assert paired_test([-1, -1, -1], 'greater')['p_valor'] == 1
    assert paired_test([-1, 0, -1], 'less')['p_valor'] == 0.25


@pytest.mark.parametrize('problem', ['duplicate', 'missing', 'nan', 'counts', 'rate', 'censor', 'balance'])
def test_invalid_input(tmp_path, problem):
    with SOURCE.open() as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    if problem == 'duplicate':
        rows.append(rows[0].copy())
    elif problem == 'missing':
        rows.pop()
    elif problem == 'nan':
        rows[0]['tempo_segundos'] = 'nan'
    elif problem == 'counts':
        rows[0]['testes_total'] = '0'
    elif problem == 'rate':
        rows[0]['taxa_sucesso'] = '0.5'
    elif problem == 'censor':
        rows[0]['censurado'] = 'sim'
    else:
        rows[0]['tratamento'] = 'sem_ia'
    path = tmp_path / 'trials.csv'
    with path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        read_trials(path)


def test_censored_trial_is_retained(tmp_path):
    with SOURCE.open() as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[0].update(tempo_segundos='2100', censurado='sim', testes_passando='3',
                   testes_falhando='3', taxa_sucesso='0.5')
    path = tmp_path / 'trials.csv'
    with path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    parsed = read_trials(path)
    assert len(parsed) == 18
    assert parsed[0]['tempo_segundos'] == 2100
    assert parsed[0]['taxa_sucesso'] == 0.5
