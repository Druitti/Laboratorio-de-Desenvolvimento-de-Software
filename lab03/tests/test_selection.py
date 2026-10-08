import json
from pathlib import Path

import pytest

from lab03.selection import (ContributorsUnavailable, RestTransport, collect, finalize, metadata, read_config,
                             read_evidence, search_candidates, timestamp)

CONFIG = Path(__file__).resolve().parents[1] / 'config.json'


@pytest.fixture
def config():
    return read_config(CONFIG)


def repo(n=1):
    return dict(id=n, full_name=f'org/repo{n}', default_branch='main',
                stargazers_count=2000, language='Python', fork=False, archived=False,
                created_at='2024-01-01T00:00:00Z')


class Fake:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        answer = next(self.replies)
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_pagination_and_dedup(config):
    client = Fake([({'items': [repo()], 'incomplete_results': False}, {'next': {}}),
                   ({'items': [repo(), repo(2)]}, {})])
    assert [r['id'] for r in search_candidates(client, config)] == [1, 2]
    assert client.calls[1][1]['page'] == 2
    assert 'created:<2026-01-01' in client.calls[0][1]['q']


def test_incomplete_search_rejected(config):
    with pytest.raises(RuntimeError, match='incompleta'):
        list(search_candidates(Fake([({'incomplete_results': True}, {})]), config))


def test_search_limit(config):
    config['max_search_results'] = 1
    assert len(list(search_candidates(Fake([({'items': [repo(), repo(2)]}, {})]), config))) == 1


def test_metadata_contributors_last_page(config):
    client = Fake([(repo(), {}), ({'total_count': 4}, {}),
                   ([{}], {'last': {'url': 'https://api.github.com/repos/org/repo1/contributors?per_page=1&page=37'}})])
    row = metadata(client, repo(), config, '2026-10-08T00:00:00Z')
    assert row['contributors'] == 37
    assert row['age_days_at_window_end'] == 731
    assert row['selection_status'] == 'pending_collectors'


@pytest.mark.parametrize('override', [{'fork': True}, {'archived': True},
                                     {'stargazers_count': 1000}, {'created_at': '2026-01-01T00:00:00Z'}])
def test_metadata_exclusions(config, override):
    client = Fake([({**repo(), **override}, {})])
    assert metadata(client, repo(), config, 'now')['selection_status'] == 'excluded_metadata'
    assert len(client.calls) == 1


def test_no_actions_skips_contributors(config):
    client = Fake([(repo(), {}), ({'total_count': 0}, {})])
    assert metadata(client, repo(), config, 'now')['selection_status'] == 'excluded_no_actions'


def test_large_history_does_not_fabricate_zero(config):
    client = Fake([(repo(), {}), ({'total_count': 1}, {}), ContributorsUnavailable('large')])
    row = metadata(client, repo(), config, 'now')
    assert row['contributors'] == ''
    assert row['contributors_status'] == 'unavailable_large_history'
    assert row['selection_status'] == 'pending_collectors'


def test_contributors_empty_and_missing_last(config):
    client = Fake([(repo(), {}), ({'total_count': 1}, {}), ([], {})])
    assert metadata(client, repo(), config, 'now')['contributors'] == 0
    client = Fake([(repo(), {}), ({'total_count': 1}, {}), ([{}], {'next': {}})])
    with pytest.raises(RuntimeError, match='última página'):
        metadata(client, repo(), config, 'now')


def test_resume_after_failure_and_config_guard(config, tmp_path):
    config['target_candidates'] = 2
    first = Fake([({'items': [repo(), repo(2)]}, {}), (repo(), {}),
                  ({'total_count': 1}, {}), ([{}], {}), RuntimeError('offline')])
    with pytest.raises(RuntimeError, match='offline'):
        collect(first, config, tmp_path)
    state = json.loads((tmp_path / 'selection_state.json').read_text())
    assert len(state['repositories']) == 1
    second = Fake([({'items': [repo(), repo(2)]}, {}), (repo(2), {}),
                   ({'total_count': 1}, {}), ([{}], {})])
    assert len(collect(second, config, tmp_path)['repositories']) == 2
    assert not any(path == '/repos/org/repo1' for path, _ in second.calls)
    assert collect(Fake([]), config, tmp_path)['repositories'] == json.loads(
        (tmp_path / 'selection_state.json').read_text())['repositories']
    config['target_candidates'] = 3
    with pytest.raises(ValueError, match='outra configuração'):
        collect(Fake([]), config, tmp_path)


def test_exhausted_is_not_complete(config, tmp_path):
    with pytest.raises(RuntimeError, match='Não é amostra completa'):
        collect(Fake([({'items': []}, {})]), config, tmp_path)


def evidence(path, config, key, count, **overrides):
    row = dict(repository='org/repo1', default_branch='main', complete=True,
               evidence_path='raw/repo1.json', **{key: count})
    row.update(overrides)
    path.write_text(json.dumps({k: config[k] for k in ('window_start', 'window_end')} |
                               {'repositories': [row]}))


@pytest.mark.parametrize('releases,runs,complete,expected', [
    (5, 50, True, 'eligible'), (4, 50, True, 'excluded_releases'),
    (5, 49, True, 'excluded_runs'), (5, 50, False, 'pending_collectors')])
def test_final_selection_thresholds(config, tmp_path, releases, runs, complete, expected):
    state = tmp_path / 'state.json'
    row = metadata(Fake([(repo(), {}), ({'total_count': 1}, {}), ([{}], {})]), repo(), config, 'now')
    state.write_text(json.dumps({'config': config, 'repositories': [row]}))
    a, b = tmp_path / 'releases.json', tmp_path / 'runs.json'
    evidence(a, config, 'stable_releases', releases, complete=complete)
    evidence(b, config, 'valid_runs', runs)
    results = finalize(state, a, b, tmp_path / 'out')
    assert results[0]['selection_status'] == expected
    payload = json.loads(a.read_text())
    payload['repositories'] = []
    a.write_text(json.dumps(payload))
    assert finalize(state, a, b, tmp_path / 'out')[0]['selection_status'] == 'pending_collectors'


def test_branch_mismatch(config, tmp_path):
    row = metadata(Fake([(repo(), {}), ({'total_count': 1}, {}), ([{}], {})]), repo(), config, 'now')
    state = tmp_path / 'state.json'
    state.write_text(json.dumps({'config': config, 'repositories': [row]}))
    a, b = tmp_path / 'releases.json', tmp_path / 'runs.json'
    evidence(a, config, 'stable_releases', 5, default_branch='other')
    evidence(b, config, 'valid_runs', 50)
    with pytest.raises(ValueError, match='branch diverge'):
        finalize(state, a, b, tmp_path / 'out')


@pytest.mark.parametrize('change', [{'complete': 'yes'}, {'stable_releases': -1}, {'evidence_path': ''}])
def test_invalid_evidence(config, tmp_path, change):
    path = tmp_path / 'e.json'
    evidence(path, config, 'stable_releases', 5, **change)
    with pytest.raises(ValueError):
        read_evidence(path, config, 'stable_releases')


def test_evidence_wrong_window_and_duplicates(config, tmp_path):
    path = tmp_path / 'e.json'
    evidence(path, config, 'stable_releases', 5)
    data = json.loads(path.read_text())
    data['repositories'] *= 2
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='duplicada'):
        read_evidence(path, config, 'stable_releases')
    data['window_end'] = '2027-01-01T00:00:00Z'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='janela'):
        read_evidence(path, config, 'stable_releases')


@pytest.mark.parametrize('change', [{'window_end': '2024-01-01T00:00:00Z'},
                                  {'target_candidates': 0}, {'max_search_results': 1001}])
def test_invalid_config(config, tmp_path, change):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config | change))
    with pytest.raises(ValueError):
        read_config(path)


def test_timezone_and_token_guards():
    with pytest.raises(ValueError):
        timestamp('2025-01-01')
    with pytest.raises(ValueError):
        RestTransport('')
    with pytest.raises(ValueError):
        RestTransport('dummy').get('https://example.org')


@pytest.mark.parametrize('status', [200, 204, 403, 500])
def test_http_status_handling(monkeypatch, status):
    class Response:
        status_code = status
        links = {}
        def json(self):
            return {'ok': True}
    transport = RestTransport('dummy')
    monkeypatch.setattr(transport.session, 'get', lambda *a, **k: Response())
    if status >= 400:
        with pytest.raises(RuntimeError, match=f'HTTP {status}'):
            transport.get('/test')
    else:
        assert transport.get('/test')[0] == ([] if status == 204 else {'ok': True})
