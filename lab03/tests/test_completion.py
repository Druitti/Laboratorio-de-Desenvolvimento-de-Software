"""Regressões da complementação #42/#43/#44, sempre com dados sintéticos."""
import json

import pytest
import requests

from lab03 import screening, selection, runs, releases
from lab03.metrics import recovery_episodes
from lab03.tests.test_http import FakeResponse, transport
from lab03.tests.test_pipeline import CONFIG, RELEASES, RUNS, FakeGitHub
from lab03.tests.test_runs import SimpleRunsAPI, run, CANDIDATE


def test_network_error_retries_without_token_in_error(tmp_path):
    client, session, clock = transport(tmp_path, [FakeResponse(200, {'ok': True})])
    original = session.get
    counter = 0
    def get(*args, **kwargs):
        nonlocal counter
        counter += 1
        if counter < 3:
            raise requests.ConnectionError('sensitive message')
        return original(*args, **kwargs)
    session.get = get
    assert client.get('/repos/o/r')[0]['ok']
    assert clock.sleeps == [1, 2]
    session.get = lambda *a, **k: (_ for _ in ()).throw(requests.Timeout('sensitive'))
    with pytest.raises(RuntimeError, match='backoff esgotado') as error:
        client.get('/repos/o/other')
    assert 'sensitive' not in str(error.value)


def test_secondary_rate_limit_retry_after(tmp_path):
    client, _, clock = transport(tmp_path, [FakeResponse(429, headers={'Retry-After': '3'}), FakeResponse(200)])
    client.get('/repos/o/r')
    assert clock.sleeps == [3]


def test_secondary_limit_exhaustion(tmp_path):
    client, _, _ = transport(tmp_path, [FakeResponse(403, {'message': 'secondary rate limit'})] * 3,
                             max_rate_limit_waits=1)
    with pytest.raises(RuntimeError, match='secundário'):
        client.get('/repos/o/r')


def test_graphql_commit_dates_batched_and_cached(tmp_path):
    client, session, _ = transport(tmp_path, [])
    shas = [f'{i:040x}' for i in range(105)]
    calls = []
    def post(url, json, timeout):
        import re
        batch = re.findall(r'c(\d+):object\(expression:"([a-f0-9]+)"\)', json['query'])
        calls.append(batch)
        return FakeResponse(200, {'data': {'repository': {f'c{i}': {'oid': sha, 'authoredDate': '2025-01-01T00:00:00Z'}
                                                         for i, sha in batch}}})
    session.post = post
    assert len(client.commit_dates('org/repo', shas)) == 105
    assert [len(b) for b in calls] == [100, 5]
    client.commit_dates('org/repo', shas)
    assert len(calls) == 2
    with pytest.raises(ValueError): client.commit_dates('org/repo', ['invalid'])


def test_graphql_errors_are_not_cached(tmp_path):
    client, session, _ = transport(tmp_path, [])
    session.post = lambda *a, **k: FakeResponse(200, {'errors': [{'message': 'error'}]})
    with pytest.raises(RuntimeError, match='GraphQL'):
        client.get('/graphql', {'query': 'query{viewer{login}}'})
    assert not list((tmp_path / 'cache').glob('*.json'))


def test_runs_truncation_never_complete():
    class API:
        def get(self, *a, **k):
            return {'total_count': 50, 'workflow_runs': [run(1, 'success')]}, {}
    with pytest.raises(releases.IncompleteCollection, match='truncados'):
        runs.collect_repository(API(), CANDIDATE, CONFIG)


def test_split_exact_cap_has_no_fractional_gap():
    start = selection.timestamp('2025-01-01T00:00:00Z')
    end = selection.timestamp('2025-01-01T00:00:05Z')
    queries = []
    class API:
        def get(self, path, params):
            queries.append(params['created'])
            return {'total_count': 1000 if len(queries) == 1 else 0, 'workflow_runs': []}, {}
    runs.fetch_window(API(), '/repos/o/r', 'main', start, end, {})
    assert queries[1].endswith('00:00:01+00:00')
    assert queries[2].startswith('2025-01-01T00:00:02+00:00')
    assert queries[2].endswith('00:00:04+00:00')


def test_wrong_branch_event_and_date_excluded():
    data = [run(1, 'success'), dict(run(2, 'failure'), head_branch='dev'),
            dict(run(3, 'failure'), event='schedule'),
            dict(run(4, 'failure'), created_at='2026-01-01T00:00:00Z')]
    raw = runs.collect_repository(SimpleRunsAPI(data), CANDIDATE, CONFIG)
    assert raw['valid_runs'] == 1 and raw['excluded_outside_scope'] == 3


def test_recovery_after_window_remains_censored():
    data = [run(1, 'success', started='2025-12-30T00:00:00Z', updated='2025-12-30T00:01:00Z'),
            run(2, 'failure', started='2025-12-31T01:00:00Z', updated='2025-12-31T01:01:00Z'),
            run(3, 'success', started='2025-12-31T23:59:00Z', updated='2026-01-01T00:00:00Z')]
    result = recovery_episodes(data, '2026-01-01T00:00:00Z')
    assert result['censored'] == 1 and result['recovery_hours'] is None


def test_screening_only_excludes_proven_upper_bounds(tmp_path):
    client = FakeGitHub({
        'org/one': {'id': 1, 'stars': 2000, 'releases': RELEASES[:2], 'runs': RUNS},
        'org/two': {'id': 2, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS[:2]},
        'org/three': {'id': 3, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    config = dict(CONFIG, target_candidates=3)
    state = selection.collect(client, config, tmp_path / 'selection')
    result, candidates = screening.screen(client, state, tmp_path / 'screening')
    assert [r['selection_status'] for r in result['repositories']] == ['excluded_releases', 'excluded_runs', 'pending_collectors']
    assert [r['repository'] for r in candidates] == ['org/three']
    calls = len(client.calls)
    screening.screen(client, state, tmp_path / 'screening')
    assert len(client.calls) == calls
    assert all(r['selection_status'] == 'pending_collectors' for r in state['repositories'])


def test_screening_failure_is_pending_and_retried(tmp_path):
    client = FakeGitHub({'org/one': {'id': 1, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    state = selection.collect(client, CONFIG, tmp_path / 'selection')
    class Offline:
        def get(self, *a, **k): raise RuntimeError('HTTP 500')
    result, candidates = screening.screen(Offline(), state, tmp_path / 'screening')
    assert not candidates and result['repositories'][0]['selection_status'] == 'pending_collectors'
    _, candidates = screening.screen(client, state, tmp_path / 'screening')
    assert len(candidates) == 1


def test_exports_preserve_other_repositories_on_partial_resume(tmp_path):
    candidates = [CANDIDATE, dict(CANDIDATE, repository='example/second')]
    api = SimpleRunsAPI([run(1, 'success')])
    runs.collect(api, CONFIG, candidates, tmp_path)
    runs.collect(api, CONFIG, candidates[:1], tmp_path)
    evidence = json.loads((tmp_path / 'runs_evidence.json').read_text())['repositories']
    assert len(evidence) == 2
    with pytest.raises(ValueError, match='outra janela'):
        releases.export_checkpoint(tmp_path, dict(CONFIG, window_end='2027-01-01T00:00:00Z'),
                                   'runs_evidence.json', 'cfr_recovery.csv')
