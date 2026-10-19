"""Fixtures offline de Tavares (#43): runs, CFR(a) e recuperação; nada é coleta real."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from lab03.metrics import change_failure_rate, recovery_episodes
from lab03.releases import IncompleteCollection
from lab03.runs import collect, collect_repository, created_qualifier, fetch_window, main, month_ranges
from lab03.selection import timestamp

CONFIG = {'window_start': '2025-01-01T00:00:00Z', 'window_end': '2025-02-01T00:00:00Z'}
CANDIDATE = {'repository': 'example/project', 'default_branch': 'main'}


def run(i, conclusion, workflow_id=1, started='2025-01-10T00:00:00Z', updated='2025-01-10T00:05:00Z'):
    return {'id': i, 'workflow_id': workflow_id, 'conclusion': conclusion,
            'head_branch': 'main', 'event': 'push', 'created_at': started,
            'run_started_at': started, 'updated_at': updated}


# --- month_ranges --------------------------------------------------------

def test_month_ranges_exact_boundaries():
    start, end = timestamp('2025-01-01T00:00:00Z'), timestamp('2026-01-01T00:00:00Z')
    ranges = list(month_ranges(start, end))
    assert len(ranges) == 12
    assert ranges[0] == (start, timestamp('2025-02-01T00:00:00Z'))
    assert ranges[-1] == (timestamp('2025-12-01T00:00:00Z'), end)


def test_month_ranges_clips_partial_window():
    start, end = timestamp('2025-03-15T00:00:00Z'), timestamp('2025-04-01T00:00:00Z')
    assert list(month_ranges(start, end)) == [(start, end)]


# --- fetch_window: paginação, dedup e subdivisão acima de 1000 -----------

class PagedRuns:
    def __init__(self, total, pages_data):
        self.total = total
        self.pages_data = pages_data
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        page = int(params.get('page', 1))
        items = self.pages_data[page - 1]
        links = ({'next': {'url': f'https://api.github.com{path}?page={page + 1}'}}
                if page < len(self.pages_data) else {})
        return {'total_count': self.total, 'workflow_runs': items}, links


def test_fetch_window_paginates_and_dedups():
    client = PagedRuns(3, [[run(1, 'success'), run(2, 'failure')], [run(2, 'failure'), run(3, 'success')]])
    runs = {}
    fetch_window(client, '/repos/o/r', 'main',
                timestamp('2025-01-01T00:00:00Z'), timestamp('2025-02-01T00:00:00Z'), runs)
    assert set(runs) == {1, 2, 3}
    assert len(client.calls) == 2


FULL_MONTH = created_qualifier(timestamp('2025-01-01T00:00:00Z'), timestamp('2025-02-01T00:00:00Z'))


class OversizedThenNormal:
    def __init__(self):
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        if params['created'] == FULL_MONTH:
            return {'total_count': 1500, 'workflow_runs': []}, {}
        return {'total_count': 1, 'workflow_runs': [run(42, 'success')]}, {}


def test_fetch_window_subdivides_over_1000():
    client = OversizedThenNormal()
    runs = {}
    fetch_window(client, '/repos/o/r', 'main',
                timestamp('2025-01-01T00:00:00Z'), timestamp('2025-02-01T00:00:00Z'), runs)
    assert 42 in runs
    assert len(client.calls) >= 3  # consulta cheia + ao menos duas metades


class AlwaysOversized:
    def get(self, path, params=None):
        return {'total_count': 2000, 'workflow_runs': []}, {}


def test_fetch_window_unsubdivisible_raises():
    with pytest.raises(IncompleteCollection):
        fetch_window(AlwaysOversized(), '/repos/o/r', 'main',
                     timestamp('2025-01-01T00:00:00Z'), timestamp('2025-01-01T00:00:04Z'), {})


class ChangingTotal:
    def __init__(self):
        self.calls = 0

    def get(self, path, params=None):
        self.calls += 1
        total = 2 if self.calls == 1 else 3
        links = {'next': {'url': f'https://api.github.com{path}?page=2'}} if self.calls == 1 else {}
        return {'total_count': total, 'workflow_runs': [run(self.calls, 'success')]}, links


def test_fetch_window_rejects_changing_total():
    with pytest.raises(IncompleteCollection):
        fetch_window(ChangingTotal(), '/repos/o/r', 'main',
                     timestamp('2025-01-01T00:00:00Z'), timestamp('2025-02-01T00:00:00Z'), {})


# --- CFR(a) ----------------------------------------------------------------

def test_cfr_only_successes():
    assert change_failure_rate([run(1, 'success'), run(2, 'success')]) == {
        'cfr_ci': 0.0, 'failures': 0, 'successes': 2, 'ignored': 0}


def test_cfr_only_failures():
    result = change_failure_rate([run(1, 'failure'), run(2, 'timed_out'), run(3, 'startup_failure')])
    assert result['cfr_ci'] == 1.0 and result['failures'] == 3


@pytest.mark.parametrize('conclusion', ['cancelled', 'skipped', 'neutral', 'action_required', 'stale', None])
def test_cfr_ignores_non_terminal_conclusions(conclusion):
    result = change_failure_rate([run(1, 'success'), run(2, conclusion)])
    assert result == {'cfr_ci': 0.0, 'failures': 0, 'successes': 1, 'ignored': 1}


def test_cfr_no_valid_runs_is_none_not_zero():
    assert change_failure_rate([run(1, 'cancelled')])['cfr_ci'] is None


# --- recuperação -------------------------------------------------------

EXAMPLE_RUNS = [
    run(1, 'success', started='2025-01-01T09:00:00Z', updated='2025-01-01T09:00:00Z'),
    run(2, 'failure', started='2025-01-01T10:00:00Z', updated='2025-01-01T10:00:00Z'),
    run(3, 'failure', started='2025-01-01T10:30:00Z', updated='2025-01-01T10:30:00Z'),
    run(4, 'success', started='2025-01-01T11:15:00Z', updated='2025-01-01T11:20:00Z'),
]


def test_recovery_example_from_statement():
    result = recovery_episodes(EXAMPLE_RUNS)
    assert result['episodes'] == 1 and result['censored'] == 0
    assert result['recovery_hours'] == pytest.approx(80 / 60)


def test_recovery_never_closed_is_censored_and_preserved():
    runs = [run(1, 'success', started='2025-01-01T09:00:00Z', updated='2025-01-01T09:00:00Z'),
           run(2, 'failure', started='2025-01-01T10:00:00Z', updated='2025-01-01T10:00:00Z')]
    result = recovery_episodes(runs)
    assert result['episodes'] == 1 and result['censored'] == 1
    assert result['recovery_hours'] is None and result['censored_ratio'] == 1.0
    assert result['details'][0] == {'workflow_id': 1, 'started_at': '2025-01-01T10:00:00Z',
                                    'recovered_at': None, 'recovery_hours': None, 'censored': True}


@pytest.mark.parametrize('conclusion', ['success', 'failure'])
def test_recovery_single_run_has_no_episode(conclusion):
    assert recovery_episodes([run(1, conclusion)])['episodes'] == 0


def test_recovery_does_not_mix_workflows():
    runs = [
        run(1, 'success', workflow_id='A', started='2025-01-01T08:00:00Z', updated='2025-01-01T08:00:00Z'),
        run(2, 'success', workflow_id='B', started='2025-01-01T08:15:00Z', updated='2025-01-01T08:15:00Z'),
        run(3, 'failure', workflow_id='B', started='2025-01-01T08:30:00Z', updated='2025-01-01T08:30:00Z'),
        run(4, 'failure', workflow_id='A', started='2025-01-01T09:00:00Z', updated='2025-01-01T09:00:00Z'),
        run(5, 'success', workflow_id='A', started='2025-01-01T10:00:00Z', updated='2025-01-01T10:00:00Z'),
        run(6, 'success', workflow_id='B', started='2025-01-01T11:00:00Z', updated='2025-01-01T11:00:00Z'),
    ]
    result = recovery_episodes(runs)
    assert result['episodes'] == 2 and result['censored'] == 0
    hours = sorted(d['recovery_hours'] for d in result['details'])
    assert hours == pytest.approx([1.0, 2.5])


def test_recovery_ignores_cancelled_inside_episode():
    runs = [run(1, 'success', started='2025-01-01T09:00:00Z', updated='2025-01-01T09:00:00Z'),
           run(2, 'failure', started='2025-01-01T10:00:00Z', updated='2025-01-01T10:00:00Z'),
           run(3, 'cancelled', started='2025-01-01T10:15:00Z', updated='2025-01-01T10:15:00Z'),
           run(4, 'success', started='2025-01-01T11:15:00Z', updated='2025-01-01T11:20:00Z')]
    result = recovery_episodes(runs)
    assert result['episodes'] == 1
    assert result['recovery_hours'] == pytest.approx(80 / 60)


# --- coleta por repositório, checkpoint e CLI ----------------------------

class SimpleRunsAPI:
    def __init__(self, runs):
        self.runs = runs
        self.calls = []
        self.fail = None

    def get(self, path, params=None):
        self.calls.append((path, params))
        if self.fail:
            raise RuntimeError(self.fail)
        return {'total_count': len(self.runs), 'workflow_runs': self.runs}, {}


def test_collect_repository_computes_valid_runs_and_metrics():
    api = SimpleRunsAPI([run(1, 'success'), run(2, 'failure'), run(3, 'cancelled')])
    raw = collect_repository(api, CANDIDATE, CONFIG)
    assert raw['complete'] and raw['valid_runs'] == 2
    assert raw['cfr']['cfr_ci'] == 0.5
    assert len(api.calls) == 1


def test_collect_repository_rejects_bad_repo_name():
    with pytest.raises(ValueError):
        collect_repository(SimpleRunsAPI([]), {**CANDIDATE, 'repository': '../oops'}, CONFIG)


def test_collect_resume_and_failure(tmp_path):
    api = SimpleRunsAPI([run(1, 'success'), run(2, 'failure')])
    rows = collect(api, CONFIG, [CANDIDATE], tmp_path)
    assert rows[0]['complete'] and rows[0]['valid_runs'] == 2
    evidence = json.loads((tmp_path / 'runs_evidence.json').read_text())
    assert evidence['repositories'][0]['valid_runs'] == 2
    calls = len(api.calls)
    collect(api, CONFIG, [CANDIDATE], tmp_path)
    assert len(api.calls) == calls  # checkpoint completo reutilizado, sem nova chamada
    with pytest.raises(ValueError):
        collect(api, CONFIG, [CANDIDATE, CANDIDATE], tmp_path)
    other = tmp_path / 'failed'
    api.fail = 'HTTP 403 forbidden'
    rows = collect(api, CONFIG, [CANDIDATE], other)
    assert rows[0]['complete'] is False and rows[0]['valid_runs'] is None
    api.fail = None
    assert collect(api, CONFIG, [CANDIDATE], other)[0]['complete']


def test_concurrent_collect_with_shared_lock_preserves_all_entries(tmp_path):
    # Regressão de #50: ver o teste equivalente em test_releases.py.
    api = SimpleRunsAPI([run(1, 'success'), run(2, 'failure')])
    lock = threading.Lock()
    candidates = [{'repository': f'org/repo{i}', 'default_branch': 'main'} for i in range(10)]

    def worker(candidate):
        collect(api, CONFIG, [candidate], tmp_path, lock=lock)

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(worker, candidates))

    evidence = json.loads((tmp_path / 'runs_evidence.json').read_text())
    assert {r['repository'] for r in evidence['repositories']} == {c['repository'] for c in candidates}
    assert all(r['complete'] for r in evidence['repositories'])


def test_collect_rejects_mismatched_checkpoint(tmp_path):
    api = SimpleRunsAPI([run(1, 'success')])
    collect(api, CONFIG, [CANDIDATE], tmp_path)
    with pytest.raises(ValueError):
        collect(api, {**CONFIG, 'window_end': '2025-03-01T00:00:00Z'}, [CANDIDATE], tmp_path)


def test_cli_with_injected_transport(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    api = SimpleRunsAPI([run(1, 'success')])
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
