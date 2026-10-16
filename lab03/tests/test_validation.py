"""Dados inteiramente sintéticos; não são a amostra-ouro do estudo."""
import subprocess
import sys

import pytest

from lab03 import validation as v


@pytest.fixture
def population(tmp_path):
    config = dict(window_start='2025-01-01T00:00:00Z', window_end='2026-01-01T00:00:00Z')
    rows, releases, runs = [], [], []
    data = tmp_path / 'data'
    for index in range(300):
        name = f'synthetic/repo{index:03}'
        rows.append(dict(repository=name, default_branch='main', selection_status='eligible'))
        base = dict(repository=name, default_branch='main', complete=True, evidence_path='fixture')
        releases.append(dict(base, stable_releases=6))
        runs.append(dict(base, valid_runs=50))
        path = data / 'raw' / name / 'releases.json'
        path.parent.mkdir(parents=True)
        records = [dict(on_default_branch=True, status='in_window', release=dict(
            id=i, draft=False, prerelease=False, published_at='2025-06-01T00:00:00Z',
            html_url=f'https://github.com/{name}/releases/tag/v{i}')) for i in range(6)]
        v.save(path, dict(config, **base, releases=records))
    v.save(data / 'releases_evidence.json', dict(config, repositories=releases))
    v.save(data / 'runs_evidence.json', dict(config, repositories=runs))
    eligible = tmp_path / 'eligible.csv'
    v.write_csv(eligible, rows, list(rows[0]))
    return eligible, data, config


def test_reproducible_blinded_sample(population, tmp_path):
    a, data, config = population
    m = v.prepare(a, data, config, tmp_path / 'first')
    rows = list(reversed(v.read_csv(a)))
    v.write_csv(a, rows, list(rows[0]))
    n = v.prepare(a, data, config, tmp_path / 'second')
    assert m['items'] == n['items']
    assert len(m['repositories']) == 60 and len(set(m['repositories'])) == 60
    assert len(m['items']) == 420
    for rater in v.RATERS:
        form = v.read_csv(tmp_path / 'first' / f'{rater}.csv')
        assert len(form) == 420 and all(r['label'] == '' for r in form)
        assert list(form[0]) == v.LABEL_FIELDS
    with pytest.raises(ValueError, match='já existe'):
        v.prepare(a, data, config, tmp_path / 'first')


@pytest.mark.parametrize('change', ['small', 'duplicate', 'candidate', 'runs', 'branch', 'window', 'raw', 'release_count', 'link'])
def test_invalid_population(population, tmp_path, change):
    a, data, config = population
    rows = v.read_csv(a)
    if change == 'small': rows.pop()
    if change == 'duplicate': rows[-1] = rows[0]
    if change == 'candidate': rows[0]['selection_status'] = 'pending_collectors'
    if change in ('small', 'duplicate', 'candidate'):
        v.write_csv(a, rows, list(rows[0]))
    if change in ('runs', 'branch', 'window'):
        p = data / 'runs_evidence.json'
        j = v.read_json(p)
        if change == 'runs': j['repositories'][0]['valid_runs'] = 49
        if change == 'branch': j['repositories'][0]['default_branch'] = 'other'
        if change == 'window': j['window_end'] = '2025-12-01T00:00:00Z'
        v.save(p, j)
    if change in ('raw', 'release_count', 'link'):
        # Alterar todos garante que a falha seja atingida independentemente do sorteio.
        for p in (data / 'raw').glob('*/*/releases.json'):
            j = v.read_json(p)
            if change == 'raw': j['complete'] = False
            if change == 'release_count': j['releases'].pop()
            if change == 'link':
                for r in j['releases']: r['release']['html_url'] = 'https://example.com'
            v.save(p, j)
    with pytest.raises(ValueError): v.prepare(a, data, config, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


@pytest.fixture
def rated(tmp_path):
    items = [dict(item_id=f'{dim}{i}', repository='synthetic/example', dimension=dim,
                  release_id=str(i) if dim == 'corrective' else '', url='https://github.com/synthetic/example')
             for dim in v.CATEGORIES for i in range(2)]
    manifest = tmp_path / 'manifest.json'
    v.save(manifest, dict(items=items))
    folder = tmp_path / 'labels'
    folder.mkdir()
    for rater in v.RATERS:
        rows = [{**item, 'label': v.CATEGORIES[item['dimension']][i % 2], 'notes': ''}
                for i, item in enumerate(items)]
        v.write_csv(folder / f'{rater}.csv', rows, v.LABEL_FIELDS)
    return manifest, folder


def test_kappa_known_values():
    assert v.agreement([['yes'] * 3, ['no'] * 3], ('yes', 'no'))['kappa'] == 1
    # Pbar=1/3, marginais 1/2, Pe=1/2 => kappa=-1/3.
    assert v.agreement([['yes', 'yes', 'no'], ['no', 'no', 'yes']], ('yes', 'no'))['kappa'] == pytest.approx(-1/3)
    assert v.agreement([['yes'] * 3], ('yes', 'no'))['kappa'] is None
    with pytest.raises(ValueError): v.agreement([], ('yes', 'no'))
    with pytest.raises(ValueError): v.agreement([['yes']], ('yes', 'no'))


@pytest.mark.parametrize('change', ['blank', 'invalid', 'duplicate', 'missing', 'extra', 'identity'])
def test_invalid_labels(rated, tmp_path, change):
    manifest, folder = rated
    path = folder / 'Druitti.csv'
    rows = v.read_csv(path)
    if change == 'blank': rows[0]['label'] = ''
    if change == 'invalid': rows[0]['label'] = 'invented'
    if change == 'duplicate': rows.append(rows[0])
    if change == 'missing': rows.pop()
    if change == 'extra': rows.append({**rows[0], 'item_id': 'extra'})
    if change == 'identity': rows[0]['url'] = 'changed'
    v.write_csv(path, rows, v.LABEL_FIELDS)
    with pytest.raises(ValueError): v.analyze(manifest, folder, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_analysis_and_unanimous_consensus(rated, tmp_path):
    manifest, folder = rated
    before = {p.name: v.digest(p) for p in folder.glob('*.csv')}
    report = v.analyze(manifest, folder, tmp_path / 'analysis')
    assert all(report[d]['kappa'] == 1 for d in v.CATEGORIES)
    decisions = tmp_path / 'analysis/consensus_review.csv'
    result = v.consensus(manifest, folder, decisions, tmp_path / 'consensus')
    assert len(result) == 6 and all(r['rationale'] == 'unanimous' for r in result)
    assert before == {p.name: v.digest(p) for p in folder.glob('*.csv')}


def test_disagreement_requires_human_decision(rated, tmp_path):
    manifest, folder = rated
    for rater, label in zip(v.RATERS, ('library_framework', 'cli', 'other')):
        path = folder / f'{rater}.csv'
        rows = v.read_csv(path)
        rows[0]['label'] = label
        v.write_csv(path, rows, v.LABEL_FIELDS)
    v.analyze(manifest, folder, tmp_path / 'analysis')
    decisions = tmp_path / 'analysis/consensus_review.csv'
    rows = v.read_csv(decisions)
    assert rows[0]['suggested_label'] == ''
    assert rows[0]['status'] == 'discussion_required'
    with pytest.raises(ValueError, match='Desacordo'):
        v.consensus(manifest, folder, decisions, tmp_path / 'consensus')
    rows[0].update(label='other', rationale='Decisão sintética de teste', confirmed_by=';'.join(v.RATERS))
    v.write_csv(decisions, rows, list(rows[0]))
    assert v.consensus(manifest, folder, decisions, tmp_path / 'consensus')[0]['label'] == 'other'


def test_decision_integrity(rated, tmp_path):
    manifest, folder = rated
    v.analyze(manifest, folder, tmp_path / 'analysis')
    path = tmp_path / 'analysis/consensus_review.csv'
    rows = v.read_csv(path)
    rows[0]['label'] = 'other'
    v.write_csv(path, rows, list(rows[0]))
    with pytest.raises(ValueError, match='unanimidade'):
        v.consensus(manifest, folder, path, tmp_path / 'out')
    rows.pop()
    v.write_csv(path, rows, list(rows[0]))
    with pytest.raises(ValueError, match='exatamente'):
        v.consensus(manifest, folder, path, tmp_path / 'out')


def test_consensus_rejects_changed_votes(rated, tmp_path):
    manifest, folder = rated
    v.analyze(manifest, folder, tmp_path / 'analysis')
    path = folder / 'Druitti.csv'
    rows = v.read_csv(path)
    rows[0]['label'] = 'other'
    v.write_csv(path, rows, v.LABEL_FIELDS)
    with pytest.raises(ValueError, match='Votos mudaram'):
        v.consensus(manifest, folder, tmp_path / 'analysis/consensus_review.csv', tmp_path / 'out')


def test_cli(rated, tmp_path):
    manifest, folder = rated
    cmd = [sys.executable, '-m', 'lab03.validation']
    result = subprocess.run(cmd + ['analyze', '--manifest', str(manifest), '--labels', str(folder),
                                  '--out', str(tmp_path / 'analysis')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(cmd + ['prepare', '--eligible', str(tmp_path / 'missing.csv'),
                                  '--data', str(tmp_path), '--out', str(tmp_path / 'new')], capture_output=True, text=True)
    assert result.returncode == 2 and 'Entrada incompleta' in result.stderr
