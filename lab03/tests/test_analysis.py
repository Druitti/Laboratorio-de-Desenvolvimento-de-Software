"""Cortes da disciplina, denominadores, pareamento e inferência estatística."""
import json

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from lab03 import analysis
from lab03 import validation as v


@pytest.mark.parametrize('metric,value,expected', [
    ('frequency', 7, 4), ('frequency', 1, 3), ('frequency', 84/365, 2),
    ('frequency', .1, 1), ('lead', 23.99, 4), ('lead', 24, 3),
    ('lead', 168, 2), ('lead', 720, 1), ('cfr', .15, 4), ('cfr', .30, 3),
    ('cfr', .45, 2), ('cfr', .46, 1), ('recovery', .99, 4),
    ('recovery', 1, 3), ('recovery', 24, 2), ('recovery', 168, 1),
])
def test_reference_cutoffs(metric, value, expected):
    assert analysis.score(value, metric) == expected


def test_general_category_floor_and_missing():
    assert analysis.category(7, 24, .31, 200) == 2  # scores 4,3,2,1 => floor(2.5)
    assert analysis.category(7, 24, .31, None) is None
    assert analysis.category(7, 24, .31, np.nan) is None
    for value in (-1, float('inf'), 1.1):
        with pytest.raises(ValueError):
            analysis.score(value, 'cfr')


def sample(n=16):
    frame = pd.DataFrame({m: np.arange(n, dtype=float) for m in analysis.METRICS})
    frame['repository'] = [f'o/r{i}' for i in range(n)]
    frame['stars'] = np.arange(n)+1001
    frame['contributors'] = np.arange(n)+1
    frame['age_days_at_window_end'] = np.arange(n)+20
    frame['cfr_ci'] = np.linspace(0, 1, n)
    frame['cfr_delivery'] = np.nan
    frame['deployment_frequency_pre'] = frame.deployment_frequency
    frame['lead_time_pre_commit_hours'] = frame.lead_time_commit_hours
    return frame


def test_descriptive_missing_is_not_zero_and_iqr():
    frame = sample(4)
    frame['recovery_hours'] = [1, 2, 3, np.nan]
    result = analysis.descriptive(frame).set_index('metric')
    assert result.loc['recovery_hours', 'median'] == 2
    assert result.loc['recovery_hours', 'iqr'] == 1
    assert result.loc['recovery_hours', 'missing'] == 1
    assert np.isnan(result.loc['cfr_delivery', 'median'])


def test_spearman_pairwise_complete_and_constant():
    frame = sample(4)
    frame.loc[3, 'cfr_ci'] = np.nan
    result = analysis.correlations(frame).iloc[0]
    assert result.n == 3 and result.rho == pytest.approx(1)
    frame['cfr_ci'] = .1
    assert analysis.correlations(frame).iloc[0].status == 'insufficient_or_constant'


def test_holm_family_and_effect_size():
    result, groups = analysis.factor_tests(sample())
    valid = result.p.notna()
    assert valid.sum() == 15  # 3 factors x 5 observed metrics; delivery is absent
    assert np.allclose(result.loc[valid, 'p_holm'], multipletests(result.loc[valid, 'p'], method='holm')[1])
    assert (result.loc[valid, 'effect'] >= 0).all()
    assert (result.loc[valid, 'effect'] <= 1).all()
    assert set(result.loc[valid, 'effect_type']) == {'epsilon_squared'}
    assert groups.n.min() == 4


def test_tied_quartiles_use_two_groups_and_signed_delta():
    frame = sample()
    frame['stars'] = [1001]*8 + [2001]*8
    result, _ = analysis.factor_tests(frame)
    row = result[(result.factor == 'stars') & (result.metric == 'deployment_frequency')].iloc[0]
    assert row.test == 'Mann-Whitney'
    assert row.effect == -1  # ascending quartiles: every observation in Q1 is smaller


def test_constant_factor_or_outcome_no_false_significance():
    frame = sample()
    frame['stars'] = 1001
    frame['recovery_hours'] = 3
    result, _ = analysis.factor_tests(frame)
    assert result[result.factor == 'stars'].p.isna().all()
    valid = result[(result.metric == 'recovery_hours') & (result.factor != 'stars')]
    assert (valid.p == 1).all() and (valid.effect == 0).all()


def test_sensitivity_paired_denominator_and_constant_kappa():
    frame = sample(4)
    frame['deployment_frequency'] = 8
    frame['deployment_frequency_pre'] = 8
    frame['cfr_ci'] = .1
    frame['lead_time_release_hours'] = 1
    frame['lead_time_commit_hours'] = 1
    frame['lead_time_pre_commit_hours'] = 1
    frame['recovery_hours'] = 0.5
    frame.loc[0, 'lead_time_pre_commit_hours'] = np.nan
    classes, pairs, _ = analysis.sensitivity(frame)
    pair = pairs[pairs.pair == 'C1 x C3'].iloc[0]
    assert pair.n == 3 and pair.excluded == 1 and pair.changed_percent == 0
    assert pd.isna(pair.kappa_linear)  # identical constant vectors: undefined, not 1
    assert classes.C4.isna().all()


def test_final_run_refuses_incomplete_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(analysis, 'build_dataset', lambda *a: (sample(), {}))
    with pytest.raises(ValueError, match='Entrega final bloqueada'):
        analysis.run(tmp_path, {}, tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_end_to_end_exploratory_exports_and_preserves_previous(tmp_path, monkeypatch):
    monkeypatch.setattr(analysis, 'build_dataset', lambda *a: (sample(), {}))
    config = {'window_start': '2025-01-01T00:00:00Z', 'window_end': '2026-01-01T00:00:00Z'}
    frame, blockers = analysis.run(tmp_path, config, tmp_path/'out', True)
    assert len(blockers) == 2
    manifest = json.loads((tmp_path/'out/manifest.json').read_text())
    assert manifest['status'] == 'exploratory_incomplete'
    assert (tmp_path/'out/rq01_04.png').stat().st_size > 1000
    assert len(pd.read_csv(tmp_path/'out/dataset.csv')) == len(frame)
    with pytest.raises(ValueError, match='já existe'):
        analysis.run(tmp_path, config, tmp_path/'out', True)


def raw_population(tmp_path, count=2):
    """Somente fixtures sintéticas: 5 releases e 50 runs por projeto."""
    data = tmp_path/'data'
    config = dict(window_start='2025-01-01T00:00:00Z', window_end='2026-01-01T00:00:00Z')
    rows, re, ru = [], [], []
    for i in range(count):
        name = f'synthetic/r{i}'
        base = dict(repository=name, default_branch='main', complete=True, **config)
        row = dict(repository=name, repository_id=i+1, default_branch='main', selection_status='eligible',
                   stars=1001+i, contributors=10+i, age_days_at_window_end=100+i)
        rows.append(row)
        path = data/'raw'/name
        path.mkdir(parents=True)
        records = [dict(on_default_branch=True, status='in_window', release=dict(
            id=j, tag_name=f'1.0.{j}', name='hotfix', body='Fix crash', prerelease=False, draft=False,
            published_at=f'2025-06-{j+1:02}T00:00:00Z', html_url=f'https://github.com/{name}/releases/tag/v{j}'))
            for j in range(5)]
        intervals = [dict(release_id=j, status='no_previous_release', commits=[],
                          published_at=r['release']['published_at']) for j, r in enumerate(records)]
        v.save(path/'releases.json', dict(base, releases=records,
               comparisons={'stable': intervals, 'with_prereleases': intervals}))
        runs = [dict(id=j, workflow_id=1, head_branch='main', event='push',
                     created_at=f'2025-06-01T00:{j:02}:00Z', run_started_at=f'2025-06-01T00:{j:02}:00Z',
                     updated_at=f'2025-06-01T00:{j:02}:30Z', conclusion='success') for j in range(50)]
        v.save(path/'runs.json', dict(base, runs=runs))
        re.append(dict(base, stable_releases=5, evidence_path='fixture'))
        ru.append(dict(base, valid_runs=50, evidence_path='fixture'))
    (data/'final_selection').mkdir()
    v.write_csv(data/'final_selection/eligible.csv', rows, list(rows[0]))
    v.save(data/'releases_evidence.json', dict(config, repositories=re))
    v.save(data/'runs_evidence.json', dict(config, repositories=ru))
    return data, config


def test_build_dataset_recomputes_and_preserves_absence(tmp_path):
    data, config = raw_population(tmp_path)
    frame, sources = analysis.build_dataset(data, config)
    assert len(frame) == 2 and len(sources) == 7
    assert frame.deployment_frequency.iloc[0] == pytest.approx(5/(365/7))
    assert (frame.cfr_ci == 0).all()
    assert frame.recovery_hours.isna().all()
    assert frame.lead_time_release_hours.isna().all()
    assert (frame.ignored_releases == 5).all()


@pytest.mark.parametrize('mutation', ['duplicate', 'scope', 'window', 'count', 'comparisons', 'complete'])
def test_build_dataset_rejects_unproven_inputs(tmp_path, mutation):
    data, config = raw_population(tmp_path)
    path = data/'raw/synthetic/r0/runs.json'
    raw = v.read_json(path)
    if mutation == 'duplicate': raw['runs'].append(raw['runs'][0])
    if mutation == 'scope': raw['runs'][0]['event'] = 'workflow_dispatch'
    if mutation == 'window': raw['window_start'] = '2024-01-01T00:00:00Z'
    if mutation == 'count': raw['runs'].pop()
    if mutation == 'complete': raw['complete'] = False
    v.save(path, raw)
    if mutation == 'comparisons':
        path = data/'raw/synthetic/r0/releases.json'
        raw = v.read_json(path)
        raw['comparisons']['stable'].pop()
        v.save(path, raw)
    with pytest.raises(ValueError):
        analysis.build_dataset(data, config)


@pytest.mark.parametrize('prediction', ['yes', 'uncertain', 'no'])
def test_gold_adapter_revalidates_votes_and_hashes(tmp_path, monkeypatch, prediction):
    data, config = raw_population(tmp_path, 300)
    gold = tmp_path/'gold'
    manifest = v.prepare(data/'final_selection/eligible.csv', data, config, gold)
    for rater in v.RATERS:
        path = gold/f'{rater}.csv'
        rows = v.read_csv(path)
        for row in rows:
            row['label'] = 'other' if row['dimension'] == 'project_type' else 'yes'
        v.write_csv(path, rows, v.LABEL_FIELDS)
    v.analyze(gold/'manifest.json', gold, tmp_path/'agreement')
    (gold/'consensus_review.csv').write_bytes((tmp_path/'agreement/consensus_review.csv').read_bytes())
    frame, _ = analysis.build_dataset(data, config)
    original = analysis.classify_repository

    def synthetic_predictions(raw):
        result = original(raw)
        for row in result['predictions']:
            row['prediction'] = prediction
        return result

    monkeypatch.setattr(analysis, 'classify_repository', synthetic_predictions)
    result, report, sources = analysis.validated_delivery(frame, data, config, gold)
    assert report['n'] == 300 and len(sources) == 5
    assert len(report['predictions']) == 1500
    assert len(report['cfr_b_by_repository']) == 300
    assert all(row['heuristic_version'] == analysis.HEURISTIC_VERSION for row in report['predictions'])
    assert all(len(repo['audit']) == 5 for repo in report['cfr_b_by_repository'].values())
    analysis.save(tmp_path/'heuristic_validation.json', report)
    exported = analysis.load(tmp_path/'heuristic_validation.json')
    assert exported['predictions'][0]['repository'] in set(frame.repository)
    assert exported['predictions'][0]['release_id'] is not None
    assert 'correction_evidence' in exported['predictions'][0]
    assert exported['cfr_b_by_repository'] == report['cfr_b_by_repository']
    if prediction == 'yes':
        assert report['f1'] == 1 and report['tp'] == 300
        assert result.cfr_delivery.iloc[0] == .8  # four followed by hotfix, last not followed
    elif prediction == 'uncertain':
        assert report['f1'] is None and report['precision'] is None and report['recall'] is None
        assert report['items_evaluated'] == 0 and report['items_excluded'] == 300
        assert report['prediction_coverage'] == 0 and report['evaluation_coverage'] == 0
        assert set(result.cfr_delivery_status) == {'validation_undefined'}
    else:
        assert report['f1'] == 0 and report['fn'] == 300 and report['precision'] is None
        assert set(result.cfr_delivery_status) == {'validation_below_threshold'}
    assert result.cfr_delivery.notna().all()
    # A changed source after sampling invalidates the frozen sample.
    path = data/'raw'/manifest['repositories'][0]/'releases.json'
    path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError, match='Fonte alterada'):
        analysis.validated_delivery(frame, data, config, gold)
