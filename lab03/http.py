"""Transporte compartilhado de Tavares (#43): cache em disco, rate limit e backoff."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

from lab03.selection import API, ContributorsUnavailable

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / 'data' / 'cache'
BACKOFF_SECONDS = (1, 2, 4, 8)


def cache_key(path, params):
    signature = json.dumps({'path': path, 'params': params or {}}, sort_keys=True, default=str)
    return hashlib.sha256(signature.encode('utf-8')).hexdigest()


class CachedTransport:
    """Mesmo contrato de RestTransport, com cache por resposta, espera de rate
    limit e backoff exponencial para erros 5xx. Nunca aceita token fora do
    ambiente; quem instancia é responsável por lê-lo de GITHUB_TOKEN."""

    def __init__(self, token, cache_dir=DEFAULT_CACHE_DIR, session=None, sleep=time.sleep,
                 now=time.time, max_retries=len(BACKOFF_SECONDS), max_rate_limit_waits=3):
        if not token:
            raise ValueError('Defina GITHUB_TOKEN no ambiente.')
        self.session = session or requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {token}',
                                     'Accept': 'application/vnd.github+json',
                                     'X-GitHub-Api-Version': '2022-11-28'})
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sleep = sleep
        self.now = now
        self.max_retries = max_retries
        self.max_rate_limit_waits = max_rate_limit_waits
        self._rate_remaining = None
        self._rate_reset = None

    def _cache_path(self, path, params):
        return self.cache_dir / f'{cache_key(path, params)}.json'

    def _load_cached(self, cache_path):
        if not cache_path.exists():
            return None
        cached = json.loads(cache_path.read_text(encoding='utf-8'))
        return cached['payload'], cached['links']

    def _save_cache(self, cache_path, payload, links):
        tmp = cache_path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'payload': payload, 'links': links}, ensure_ascii=False), encoding='utf-8')
        tmp.replace(cache_path)

    def _update_rate_limit(self, headers):
        remaining = headers.get('X-RateLimit-Remaining')
        reset = headers.get('X-RateLimit-Reset')
        if remaining is not None:
            self._rate_remaining = int(remaining)
        if reset is not None:
            self._rate_reset = int(reset)

    def _wait_for_rate_limit(self):
        if self._rate_remaining == 0 and self._rate_reset is not None:
            wait = self._rate_reset - self.now() + 1
            if wait > 0:
                self.sleep(wait)

    def get(self, path, params=None):
        # Não aceita URLs externas nem imprime cabeçalhos/credenciais.
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Endpoint precisa ser um caminho relativo à API GitHub.')
        cache_path = self._cache_path(path, params)
        cached = self._load_cached(cache_path)
        if cached is not None:
            return cached
        backoff_attempt = 0
        rate_limit_waits = 0
        while True:
            self._wait_for_rate_limit()
            response = self.session.get(API + path, params=params, timeout=45)
            self._update_rate_limit(response.headers)
            if response.status_code in (403, 429) and self._rate_remaining == 0:
                if rate_limit_waits >= self.max_rate_limit_waits:
                    raise RuntimeError(f'HTTP {response.status_code} em {path}; '
                                       'rate limit não liberou após espera repetida.')
                rate_limit_waits += 1
                continue
            if response.status_code >= 500:
                if backoff_attempt >= self.max_retries:
                    raise RuntimeError(f'HTTP {response.status_code} em {path}; backoff esgotado.')
                self.sleep(BACKOFF_SECONDS[backoff_attempt])
                backoff_attempt += 1
                continue
            if response.status_code == 204:
                payload, links = [], dict(response.links)
            elif response.status_code != 200:
                if (response.status_code == 403 and path.endswith('/contributors')
                        and 'too large to list contributors' in response.json().get('message', '')):
                    raise ContributorsUnavailable(path)
                raise RuntimeError(f'HTTP {response.status_code} em {path}; '
                                   'retome após resolver acesso/cota. Nenhum erro é contado como ausência.')
            else:
                payload, links = response.json(), dict(response.links)
            self._save_cache(cache_path, payload, links)
            return payload, links
