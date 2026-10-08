"""Fixtures offline de Santiago (#42): nada aqui é amostra real do GitHub."""
import copy
import json
from pathlib import Path

import pytest

from lab03.metrics import lead_time
from lab03.releases import (IncompleteCollection, collect, collect_repository,
                            compare_commits, is_404, main, pages)
from lab03.selection import read_evidence

CONFIG = {'window_start': '2025-01-01T00:00:00Z', 'window_end': '2026-01-01T00:00:00Z'}
CANDIDATE = {'repository': 'example/project', 'default_branch': 'main'}


def commit(sha, date='2025-03-02T00:00:00Z'):
    return {'sha': sha, 'commit': {'author': {'date': date}, 'message': 'fix: example'}}


def release(i, tag, date, **extra):
    return dict(id=i, tag_name=tag, published_at=date, draft=False, prerelease=False,
                target_commitish='misleading-target', **extra)


@pytest.fixture
def example_interval():
    return {'release_id': 2, 'head_tag': 'v1.1', 'base_tag': 'v1.0', 'status': 'ok',
            'published_at': '2025-03-15T00:00:00Z',
            'commits': [commit('a'), commit('b', '2025-03-10T00:00:00Z'),
                        commit('c', '2025-03-14T00:00:00Z')]}


@pytest.fixture
def api():
    class API:
        def __init__(self):
            self.calls = []
            self.items = [release(1, 'v0', '2024-12-01T00:00:00Z'),
                          release(2, 'v1', '2025-03-15T00:00:00Z'),
                          release(3, 'v2', '2025-04-15T00:00:00Z'),
                          release(4, 'pre', '2025-03-20T00:00:00Z'),
                          release(5, 'side', '2025-03-01T00:00:00Z'),
                          release(6, 'end', CONFIG['window_end']),
                          release(7, 'draft', CONFIG['window_start'])]
            self.items[3]['prerelease'] = True
            self.items[6]['draft'] = True
            self.fail = None
            self.compare_error = None
        def get(self, path, params=None):
            self.calls.append((path, params))
            if self.fail:
                raise RuntimeError(self.fail)
            if path.endswith('/releases'):
                if int(params['page']) == 1:
                    return list(reversed(self.items[2:])), {'next': {'url': 'https://api.github.com' + path + '?per_page=100&page=2'}}
                return self.items[:2], {}
            if path.endswith('/tags'):
                return [{'name': 'v1', 'commit': {'sha': 'v1'}},
                        {'name': 'old', 'commit': {'sha': 'old'}},
                        {'name': 'side', 'commit': {'sha': 'side'}}], {}
            if '/commits/' in path:
                ref = path.rsplit('/', 1)[-1]
                return commit('HEAD' if ref == 'main' else ref,
                              '2024-12-01T00:00:00Z' if ref == 'old' else '2025-03-02T00:00:00Z'), {}
            if path.endswith('...HEAD'):
                return {'status': 'diverged' if '/side...' in path else 'ahead'}, {}
            if '/compare/' in path:
                if self.compare_error:
                    raise RuntimeError(self.compare_error)
                return {'total_commits': 3, 'status': 'ahead',
                        'commits': [commit('a'), commit('b', '2025-03-10T00:00:00Z'),
                                    commit('c', '2025-03-14T00:00:00Z')]}, {}
            raise AssertionError(path)
    return API()


def test_example_and_weighting(example_interval):
    result = lead_time([example_interval])
    assert result['lead_time_release_hours'] == 13 * 24
    assert result['lead_time_commit_hours'] == 5 * 24
    second = {**example_interval, 'commits': [commit('d', '2025-03-14T00:00:00Z')]}
    result = lead_time([example_interval, second])
    assert result['lead_time_release_hours'] == 7 * 24
    assert result['lead_time_commit_hours'] == 3 * 24
    assert result['measured_commit_inclusions'] == 4


@pytest.mark.parametrize('status', ['no_previous_release', 'compare_404', 'non_forward_history'])
def test_missing_not_zero(status, example_interval):
    result = lead_time([{**example_interval, 'status': status}])
    assert result['lead_time_release_hours'] is None
    assert result['lead_time_commit_hours'] is None
    assert result['ignored_releases'] == 1


@pytest.mark.parametrize('date', ['bad', '2025-03-16T00:00:00Z', None, '2025-03-02'])
def test_inconsistent_dates(date, example_interval):
    result = lead_time([{**example_interval, 'commits': [commit('a', date)]}])
    assert result['intervals'][0]['status'] == 'inconsistent_dates'
    assert result['lead_time_commit_hours'] is None


def test_no_commits_and_duplicates(example_interval):
    assert lead_time([{**example_interval, 'commits': []}])['intervals'][0]['status'] == 'no_commits'
    interval = copy.deepcopy(example_interval)
    interval['commits'].append(interval['commits'][0])
    assert lead_time([interval])['measured_commit_inclusions'] == 3
    assert lead_time([])['measured_releases'] == 0
    malformed = {**example_interval, 'commits': [{'sha': 'a'}]}
    assert lead_time([malformed])['intervals'][0]['status'] == 'inconsistent_dates'


def test_branch_previous_and_variants(api):
    raw = collect_repository(api, CANDIDATE, CONFIG)
    assert raw['complete'] and raw['stable_releases'] == 2
    intervals = raw['comparisons']['stable']
    assert intervals[0]['base_tag'] == 'v0'
    assert intervals[1]['base_tag'] == 'v1'
    assert len(raw['comparisons']['with_prereleases']) == 3
    assert raw['comparisons']['with_prereleases'][-1]['base_tag'] == 'pre'
    assert [t['in_window'] for t in raw['tags']] == [True, False, True]
    assert raw['tags'][-1]['on_default_branch'] is False
    assert not any('/commits/end' in path or '/commits/draft' in path for path, _ in api.calls)
    assert raw['branch_sha'] == 'HEAD'


def test_boundaries_and_first_release(api):
    api.items = [release(1, 'v1', CONFIG['window_start'])]
    raw = collect_repository(api, CANDIDATE, CONFIG)
    assert raw['stable_releases'] == 1
    assert raw['metrics']['stable']['lead_time_release_hours'] is None
    assert raw['comparisons']['stable'][0]['status'] == 'no_previous_release'


def test_404_compare_auditable(api):
    api.compare_error = 'HTTP 404 em /compare'
    raw = collect_repository(api, CANDIDATE, CONFIG)
    assert raw['complete']
    assert raw['metrics']['stable']['ignored_releases'] == 2
    assert raw['comparisons']['stable'][0]['status'] == 'compare_404'


def test_unresolved_release_not_zero(api):
    old = api.get
    def get(path, params=None):
        if path.endswith('/commits/v1'):
            raise RuntimeError('HTTP 404 em /commits/v1')
        return old(path, params)
    api.get = get
    raw = collect_repository(api, CANDIDATE, CONFIG)
    assert not raw['complete'] and raw['stable_releases'] is None
    assert raw['unresolved_release_tags'] == 1


def test_compare_over_250_and_dedup():
    class Many:
        def get(self, path, params):
            page = int(params['page'])
            start, end = (page - 1) * 100, min(page * 100, 301)
            data = [commit(str(i)) for i in range(start, end)]
            links = {'next': {'url': f'https://api.github.com{path}?per_page=100&page={page+1}'}} if page < 4 else {}
            return {'total_commits': 301, 'status': 'ahead', 'commits': data}, links
    commits, status = compare_commits(Many(), '/repos/o/r', 'a', 'b')
    assert len(commits) == 301 and status == 'ahead'


@pytest.mark.parametrize('kind', ['truncated', 'changed'])
def test_reject_bad_compare(kind):
    class Bad:
        def get(self, path, params):
            page = int(params['page'])
            links = {'next': {'url': f'https://api.github.com{path}?page=2'}} if kind == 'changed' and page == 1 else {}
            return {'total_commits': page + 1, 'status': 'ahead', 'commits': [commit(str(page))]}, links
    with pytest.raises(IncompleteCollection):
        compare_commits(Bad(), '/repos/o/r', 'a', 'b')


@pytest.mark.parametrize('url', ['https://evil.example/repos/o/r/releases?page=2',
                              'https://api.github.com/repos/o/other/releases?page=2',
                              'https://api.github.com/repos/o/r/releases?per_page=100&page=1'])
def test_bad_links(url):
    class Bad:
        def get(self, path, params):
            return [], {'next': {'url': url}}
    with pytest.raises(IncompleteCollection):
        list(pages(Bad(), '/repos/o/r/releases'))


def test_export_resume_and_failure(api, tmp_path):
    rows = collect(api, CONFIG, [CANDIDATE], tmp_path)
    assert rows[0]['complete']
    assert read_evidence(tmp_path / 'releases_evidence.json', CONFIG, 'stable_releases')
    calls = len(api.calls)
    collect(api, CONFIG, [CANDIDATE], tmp_path)
    assert len(api.calls) == calls
    with pytest.raises(ValueError):
        collect(api, {**CONFIG, 'window_end': '2027-01-01T00:00:00Z'}, [CANDIDATE], tmp_path)
    with pytest.raises(ValueError):
        collect(api, CONFIG, [CANDIDATE, CANDIDATE], tmp_path)
    other = tmp_path / 'failed'
    api.fail = 'HTTP 403 forbidden'
    rows = collect(api, CONFIG, [CANDIDATE], other)
    assert rows[0]['complete'] is False and rows[0]['stable_releases'] is None
    assert read_evidence(other / 'releases_evidence.json', CONFIG, 'stable_releases')
    api.fail = None
    assert collect(api, CONFIG, [CANDIDATE], other)[0]['complete']


def test_invalid_release_date_and_repo(api):
    api.items[1]['published_at'] = None
    with pytest.raises(IncompleteCollection):
        collect_repository(api, CANDIDATE, CONFIG)
    with pytest.raises(ValueError):
        collect_repository(api, {**CANDIDATE, 'repository': '../oops'}, CONFIG)


def test_errors_propagate(api):
    api.compare_error = 'HTTP 500 error'
    with pytest.raises(RuntimeError):
        collect_repository(api, CANDIDATE, CONFIG)
    class Error:
        status_code = 404
    assert is_404(Error())
    assert not is_404(RuntimeError('HTTP 403'))


def test_cli_with_injected_transport(api, tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    config = {**CONFIG, 'target_candidates': 1, 'max_search_results': 1000,
              'min_stars': 1000, 'min_releases': 5, 'min_valid_runs': 50}
    (tmp_path / 'config.json').write_text(json.dumps(config))
    (tmp_path / 'candidates.csv').write_text('repository,default_branch\nexample/project,main\n')
    monkeypatch.setitem(sys.modules, 'fake_transport', SimpleNamespace(factory=lambda: api))
    args = ['--config', str(tmp_path / 'config.json'), '--candidates', str(tmp_path / 'candidates.csv'),
            '--out', str(tmp_path / 'out'), '--transport', 'fake_transport:factory', '--limit', '1']
    assert main(args) == 0
    api.fail = 'HTTP 429'
    args[5] = str(tmp_path / 'failed')
    assert main(args) == 1


def test_unknown_count_stays_pending_in_finalizer(api, tmp_path):
    from lab03.selection import FIELDS, finalize
    api.fail = 'HTTP 403'
    collect(api, CONFIG, [CANDIDATE], tmp_path)
    row = {field: '' for field in FIELDS}
    row.update(CANDIDATE, selection_status='pending_collectors')
    state = {'config': CONFIG, 'repositories': [row]}
    (tmp_path / 'state.json').write_text(json.dumps(state))
    runs = {**CONFIG, 'repositories': [{**CANDIDATE, 'complete': True, 'valid_runs': 100,
                                        'evidence_path': 'fixture-only.json'}]}
    (tmp_path / 'runs.json').write_text(json.dumps(runs))
    result = finalize(tmp_path / 'state.json', tmp_path / 'releases_evidence.json',
                      tmp_path / 'runs.json', tmp_path / 'final')
    assert result[0]['selection_status'] == 'pending_collectors'
    evidence = json.loads((tmp_path / 'releases_evidence.json').read_text())
    evidence['repositories'][0]['complete'] = True
    (tmp_path / 'releases_evidence.json').write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match='Contagem inválida'):
        read_evidence(tmp_path / 'releases_evidence.json', CONFIG, 'stable_releases')


def test_progress_logs_resume_and_safe_error(api, tmp_path, caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger='lab03.releases')
    collect(api, CONFIG, [CANDIDATE], tmp_path)
    assert '[1/1] example/project | iniciando' in caplog.text
    assert 'página 2' in caplog.text
    assert 'lead time calculado' in caplog.text
    assert 'evidências salvas' in caplog.text
    caplog.clear()
    collect(api, CONFIG, [CANDIDATE], tmp_path)
    assert 'checkpoint completo reutilizado' in caplog.text
    assert 'consultando...' not in caplog.text
    caplog.clear()
    api.fail = 'HTTP 403 token=SENSITIVE_TEST_VALUE'
    collect(api, CONFIG, [CANDIDATE], tmp_path / 'failed')
    assert 'coleta pendente: RuntimeError (HTTP 403)' in caplog.text
    assert 'SENSITIVE_TEST_VALUE' not in caplog.text
