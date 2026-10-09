"""Transporte de Tavares (#43): cache, rate limit e backoff, sem tocar a rede."""
import pytest

from lab03.selection import ContributorsUnavailable
from lab03.http import BACKOFF_SECONDS, CachedTransport, cache_key


class FakeResponse:
    def __init__(self, status_code, payload=None, links=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.links = links or {}
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.responses.pop(0)


class FakeClock:
    def __init__(self, start=0):
        self.value = start
        self.sleeps = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


def transport(tmp_path, responses, **kwargs):
    clock = FakeClock()
    session = FakeSession(responses)
    client = CachedTransport('token', cache_dir=tmp_path / 'cache', session=session,
                             sleep=clock.sleep, now=clock.now, **kwargs)
    return client, session, clock


def test_cache_key_ignores_param_order():
    assert cache_key('/x', {'a': 1, 'b': 2}) == cache_key('/x', {'b': 2, 'a': 1})
    assert cache_key('/x', {'a': 1}) != cache_key('/x', {'a': 2})


def test_rejects_absolute_or_external_path(tmp_path):
    client, session, _ = transport(tmp_path, [])
    with pytest.raises(ValueError):
        client.get('https://evil.example/repos/o/r')
    with pytest.raises(ValueError):
        client.get('//evil.example/repos/o/r')
    assert session.calls == []


def test_success_is_cached_and_not_requested_twice(tmp_path):
    client, session, _ = transport(tmp_path, [FakeResponse(200, {'ok': True}, {'next': {'url': 'x'}})])
    payload, links = client.get('/repos/o/r', {'page': 1})
    assert payload == {'ok': True} and links == {'next': {'url': 'x'}}
    assert len(session.calls) == 1
    payload2, links2 = client.get('/repos/o/r', {'page': 1})
    assert payload2 == payload and links2 == links
    assert len(session.calls) == 1  # segunda chamada veio do cache em disco


def test_cache_persists_across_instances(tmp_path):
    client, session, _ = transport(tmp_path, [FakeResponse(200, {'ok': 1})])
    client.get('/repos/o/r')
    assert len(list((tmp_path / 'cache').glob('*.json'))) == 1
    reloaded, session2, _ = transport(tmp_path, [])
    payload, _ = reloaded.get('/repos/o/r')
    assert payload == {'ok': 1}
    assert session2.calls == []


def test_204_returns_empty_list(tmp_path):
    client, session, _ = transport(tmp_path, [FakeResponse(204, headers={})])
    payload, links = client.get('/repos/o/r')
    assert payload == []


def test_error_is_not_cached_and_is_retried_next_time(tmp_path):
    client, session, _ = transport(tmp_path, [FakeResponse(404, {'message': 'nope'})])
    with pytest.raises(RuntimeError, match='HTTP 404'):
        client.get('/repos/o/r')
    assert list((tmp_path / 'cache').glob('*.json')) == []
    client2, session2, _ = transport(tmp_path, [FakeResponse(200, {'ok': True})])
    payload, _ = client2.get('/repos/o/r')
    assert payload == {'ok': True}
    assert len(session2.calls) == 1


def test_contributors_unavailable_preserved(tmp_path):
    client, session, _ = transport(tmp_path, [FakeResponse(
        403, {'message': 'Sorry, this repository is too large to list contributors for via the API.'})])
    with pytest.raises(ContributorsUnavailable):
        client.get('/repos/o/r/contributors')


def test_backoff_exponential_then_success(tmp_path):
    responses = [FakeResponse(503) for _ in range(3)] + [FakeResponse(200, {'ok': True})]
    client, session, clock = transport(tmp_path, responses)
    payload, _ = client.get('/repos/o/r')
    assert payload == {'ok': True}
    assert clock.sleeps == list(BACKOFF_SECONDS[:3])
    assert len(session.calls) == 4


def test_backoff_exhausted_raises(tmp_path):
    responses = [FakeResponse(500) for _ in range(len(BACKOFF_SECONDS) + 1)]
    client, session, clock = transport(tmp_path, responses)
    with pytest.raises(RuntimeError, match='backoff esgotado'):
        client.get('/repos/o/r')
    assert clock.sleeps == list(BACKOFF_SECONDS)


def test_rate_limit_waits_until_reset(tmp_path):
    reset_at = 1000
    responses = [FakeResponse(403, {'message': 'rate limited'},
                              headers={'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': str(reset_at)}),
                FakeResponse(200, {'ok': True}, headers={'X-RateLimit-Remaining': '10'})]
    client, session, clock = transport(tmp_path, responses)
    clock.value = reset_at - 500
    payload, _ = client.get('/repos/o/r')
    assert payload == {'ok': True}
    assert clock.sleeps == [501]
    assert len(session.calls) == 2


def test_rate_limit_gives_up_after_max_waits(tmp_path):
    reset_at = 1000
    responses = [FakeResponse(403, {}, headers={'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': str(reset_at)})
                for _ in range(5)]
    client, session, clock = transport(tmp_path, responses, max_rate_limit_waits=2)
    clock.value = reset_at
    with pytest.raises(RuntimeError, match='rate limit não liberou'):
        client.get('/repos/o/r')
    assert len(session.calls) == 3


def test_requires_token():
    with pytest.raises(ValueError):
        CachedTransport('')
