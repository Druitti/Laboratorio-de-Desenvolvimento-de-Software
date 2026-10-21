"""Integração de Tavares (#44): seleção + releases + runs com um transporte fake único."""
import json

import pytest

from lab03 import pipeline
from lab03.pipeline import main, run

CONFIG = {'window_start': '2025-01-01T00:00:00Z', 'window_end': '2026-01-01T00:00:00Z',
         'target_candidates': 1, 'max_search_results': 1000, 'min_stars': 1000,
         'min_releases': 5, 'min_valid_runs': 50}


def make_release(i, month):
    return {'id': i, 'tag_name': f'v{i}', 'published_at': f'2025-{month:02d}-01T00:00:00Z',
            'draft': False, 'prerelease': False}


RELEASES = [make_release(i, i) for i in range(1, 6)]


def make_run(i):
    return {'id': i, 'workflow_id': 1, 'conclusion': 'success' if i % 2 else 'failure',
            'head_branch': 'main', 'event': 'push', 'created_at': '2025-06-01T00:00:00Z',
            'run_started_at': '2025-06-01T00:00:00Z', 'updated_at': '2025-06-01T00:05:00Z'}


RUNS = [make_run(i) for i in range(1, 61)]


class FakeGitHub:
    """Serve só o suficiente de cada endpoint para exercitar a integração real
    de selection+releases+runs; não valida nuances de cada coletor isoladamente
    (isso já é feito nos testes próprios de cada módulo)."""

    def __init__(self, repos):
        self.repos = repos
        self.calls = []

    def _item(self, name):
        data = self.repos[name]
        return {'id': data['id'], 'full_name': name, 'default_branch': data.get('branch', 'main'),
                'stargazers_count': data['stars'], 'language': 'Python', 'fork': False, 'archived': False,
                'created_at': data.get('created_at', '2020-01-01T00:00:00Z')}

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == '/search/repositories':
            items = [self._item(name) for name in self.repos]
            return {'items': items, 'incomplete_results': False, 'total_count': len(items)}, {}
        for name, data in self.repos.items():
            prefix = f'/repos/{name}'
            if path == prefix:
                return self._item(name), {}
            if path == f'{prefix}/actions/workflows':
                return {'total_count': 1}, {}
            if path == f'{prefix}/contributors':
                return [{}], {}
            if path == f'{prefix}/releases':
                return list(reversed(data['releases'])), {}
            if path == f'{prefix}/tags':
                return [], {}
            if path.startswith(f'{prefix}/commits/'):
                ref = path.rsplit('/', 1)[-1]
                return {'sha': ref, 'commit': {'author': {'date': '2025-01-02T00:00:00Z'}}}, {}
            if path.startswith(f'{prefix}/compare/'):
                return {'status': 'ahead', 'total_commits': 0, 'commits': []}, {}
            if path == f'{prefix}/actions/runs':
                return {'total_count': len(data['runs']), 'workflow_runs': data['runs']}, {}
        raise AssertionError(path)


def test_pipeline_happy_path_reaches_eligible(tmp_path):
    client = FakeGitHub({'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    results = run(CONFIG, tmp_path, client)
    assert len(results) == 1 and results[0]['selection_status'] == 'eligible'
    assert json.loads((tmp_path / 'releases_evidence.json').read_text())['repositories'][0]['stable_releases'] == 5
    assert json.loads((tmp_path / 'runs_evidence.json').read_text())['repositories'][0]['valid_runs'] == 60


class FakeGitHubWithCachePrune(FakeGitHub):
    """Simula o método de CachedTransport sem depender de disco real."""
    def __init__(self, repos):
        super().__init__(repos)
        self.prune_calls = []

    def prune_cache(self, max_bytes):
        self.prune_calls.append(max_bytes)
        return False


def test_pipeline_processes_candidates_concurrently_without_losing_any(tmp_path):
    # Regressão de #50: antes da paralelização, cada candidato era processado
    # um de cada vez; agora vários threads escrevem no mesmo
    # releases_evidence.json/runs_evidence.json concorrentemente (via lock em
    # lab03.releases.collect/lab03.runs.collect) e nenhum pode sumir.
    repos = {f'org/repo{i}': {'id': i, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS} for i in range(1, 11)}
    client = FakeGitHub(repos)
    config = {**CONFIG, 'target_candidates': 10}
    results = run(config, tmp_path, client, max_workers=10)
    assert len(results) == 10
    assert all(r['selection_status'] == 'eligible' for r in results)
    evidence = json.loads((tmp_path / 'releases_evidence.json').read_text())
    assert {r['repository'] for r in evidence['repositories']} == set(repos)


def test_pipeline_prunes_cache_when_client_supports_it(tmp_path):
    client = FakeGitHubWithCachePrune({'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    run(CONFIG, tmp_path, client)
    assert client.prune_calls == [pipeline.CACHE_PRUNE_BYTES]


def test_pipeline_ignores_transport_without_prune_support(tmp_path):
    # FakeGitHub não tem prune_cache; o transporte injetável (--transport) ou
    # de outros testes pode legitimamente não suportar poda de cache.
    client = FakeGitHub({'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    assert run(CONFIG, tmp_path, client)[0]['selection_status'] == 'eligible'


def test_pipeline_expands_when_not_enough_eligible(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'TARGET_STEP', 1)
    client = FakeGitHub({
        'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES[:2], 'runs': RUNS},
        'org/repo2': {'id': 2, 'stars': 1500, 'releases': RELEASES, 'runs': RUNS},
    })
    results = run(CONFIG, tmp_path, client)
    statuses = {r['repository']: r['selection_status'] for r in results}
    assert statuses == {'org/repo1': 'excluded_releases', 'org/repo2': 'eligible'}


class AlwaysFailingReleases(FakeGitHub):
    def get(self, path, params=None):
        if '/compare/' in path:
            raise RuntimeError('HTTP 500 simulated')
        return super().get(path, params)


def test_pipeline_raises_after_max_pending_retries(tmp_path):
    client = AlwaysFailingReleases({'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    with pytest.raises(RuntimeError, match='seguem pendentes'):
        run(CONFIG, tmp_path, client)


def test_pipeline_raises_when_expansion_exceeds_search_cap(tmp_path):
    config = {**CONFIG, 'max_search_results': 1}
    client = FakeGitHub({'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES[:2], 'runs': RUNS}})
    with pytest.raises(RuntimeError, match='max_search_results'):
        run(config, tmp_path, client)


def test_pipeline_resume_does_not_repeat_completed_calls(tmp_path):
    client = FakeGitHub({'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    run(CONFIG, tmp_path, client)
    calls = len(client.calls)
    run(CONFIG, tmp_path, client)
    assert len(client.calls) == calls


def test_cli_with_injected_transport(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    client = FakeGitHub({'org/repo1': {'id': 1, 'stars': 2000, 'releases': RELEASES, 'runs': RUNS}})
    (tmp_path / 'config.json').write_text(json.dumps(CONFIG))
    monkeypatch.setitem(sys.modules, 'fake_pipeline_transport', SimpleNamespace(factory=lambda: client))
    args = ['--config', str(tmp_path / 'config.json'), '--out', str(tmp_path / 'out'),
            '--transport', 'fake_pipeline_transport:factory']
    assert main(args) == 0
