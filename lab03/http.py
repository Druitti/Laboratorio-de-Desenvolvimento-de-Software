"""Transporte compartilhado de Tavares (#43): cache em disco, rate limit e backoff."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

from lab03.selection import API, ContributorsUnavailable

LOG = logging.getLogger(__name__)
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
        self._server_time_offset = 0.0
        self._rate_lock = threading.Lock()

    def _cache_path(self, path, params):
        return self.cache_dir / f'{cache_key(path, params)}.json'

    def cache_size_bytes(self):
        return sum(f.stat().st_size for f in self.cache_dir.glob('*.json'))

    def prune_cache(self, max_bytes):
        """Apaga todo o cache em disco quando ultrapassa max_bytes.

        O cache só evita repetir uma chamada idêntica; o progresso real de uma
        coleta longa fica em raw/*.json e nos arquivos de evidência (#43/#50),
        não aqui. Apagá-lo nunca perde trabalho concluído — na pior hipótese,
        uma chamada ainda em andamento precisa ir à rede de novo. Mantém o uso
        de disco previsível em coletas de centenas de repositórios.
        """
        if self.cache_size_bytes() <= max_bytes:
            return False
        for cached in self.cache_dir.glob('*.json'):
            cached.unlink()
        return True

    def _load_cached(self, cache_path):
        if not cache_path.exists():
            return None
        cached = json.loads(cache_path.read_text(encoding='utf-8'))
        return cached['payload'], cached['links']

    def _save_cache(self, cache_path, payload, links):
        # Sufixo único por thread: chamadas concorrentes para o mesmo path+params
        # (ex.: /search/repositories) não podem compartilhar o mesmo arquivo .tmp.
        tmp = cache_path.with_suffix(f'.{threading.get_ident()}.tmp')
        tmp.write_text(json.dumps({'payload': payload, 'links': links}, ensure_ascii=False), encoding='utf-8')
        tmp.replace(cache_path)

    def _update_rate_limit(self, headers):
        remaining = headers.get('X-RateLimit-Remaining')
        reset = headers.get('X-RateLimit-Reset')
        server_date = headers.get('Date')
        with self._rate_lock:
            if remaining is not None:
                self._rate_remaining = int(remaining)
            if reset is not None:
                self._rate_reset = int(reset)
            if server_date is not None:
                try:
                    # Relógio local pode estar errado (visto em execução real: ~11h de
                    # desvio fez uma espera de rate limit parecer de 8h+ em vez de <1h).
                    # Calibra contra a hora do servidor a cada resposta, sem exigir
                    # NTP nem privilégio de admin na máquina.
                    self._server_time_offset = parsedate_to_datetime(server_date).timestamp() - self.now()
                except (TypeError, ValueError):
                    pass

    def _wait_for_rate_limit(self):
        with self._rate_lock:
            remaining, reset, offset = self._rate_remaining, self._rate_reset, self._server_time_offset
        if remaining == 0 and reset is not None:
            wait = reset - (self.now() + offset) + 1
            if wait > 0:
                # Sem log aqui, uma pausa de rate limit primário parece uma
                # coleta travada — já visto em execução real com paralelismo (#50).
                LOG.warning('Cota primária esgotada; aguardando %.0fs até o reset.', wait)
                self.sleep(wait)

    def get(self, path, params=None):
        # Não aceita URLs externas nem imprime cabeçalhos/credenciais.
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Endpoint precisa ser um caminho relativo à API GitHub.')
        cache_path = self._cache_path(path, params)
        cached = self._load_cached(cache_path)
        if (cached is not None and path == '/search/repositories'
                and cached[0].get('incomplete_results')):
            cached = None  # Uma busca incompleta antiga não pode impedir a retomada.
        if cached is not None:
            return cached
        backoff_attempt = 0
        rate_limit_waits = 0
        while True:
            self._wait_for_rate_limit()
            try:
                response = (self.session.post(API + path, json=params, timeout=45) if path == '/graphql'
                            else self.session.get(API + path, params=params, timeout=45))
            except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
                if backoff_attempt >= self.max_retries:
                    raise RuntimeError(f'Falha de rede em {path}; backoff esgotado.') from None
                wait = BACKOFF_SECONDS[min(backoff_attempt, len(BACKOFF_SECONDS) - 1)]
                LOG.warning('Falha de rede em %s; nova tentativa em %ss.', path, wait)
                self.sleep(wait)
                backoff_attempt += 1
                continue
            self._update_rate_limit(response.headers)
            if response.status_code in (403, 429) and self._rate_remaining == 0:
                if rate_limit_waits >= self.max_rate_limit_waits:
                    raise RuntimeError(f'HTTP {response.status_code} em {path}; '
                                       'rate limit não liberou após espera repetida.')
                LOG.warning('HTTP %s em %s com cota zerada; aguardando o reset via _wait_for_rate_limit.',
                           response.status_code, path)
                rate_limit_waits += 1
                continue
            if response.status_code == 429 or (response.status_code == 403 and
                    ('Retry-After' in response.headers or 'secondary rate limit' in response.text.lower())):
                if rate_limit_waits >= self.max_rate_limit_waits:
                    raise RuntimeError(f'HTTP {response.status_code} em {path}; limite secundário persistente.')
                try:
                    wait = max(1, float(response.headers.get('Retry-After', 60)))
                except ValueError:
                    wait = 60
                # Limite secundário/anti-abuso do GitHub: a cota primária
                # (X-RateLimit-*) pode continuar alta mesmo durante essa espera,
                # por isso só este log explica uma pausa longa (#50).
                LOG.warning('Limite secundário de rate limit em %s (HTTP %s); aguardando %.0fs.',
                           path, response.status_code, wait)
                self.sleep(wait)
                rate_limit_waits += 1
                continue
            if response.status_code >= 500:
                if backoff_attempt >= self.max_retries:
                    raise RuntimeError(f'HTTP {response.status_code} em {path}; backoff esgotado.')
                wait = BACKOFF_SECONDS[min(backoff_attempt, len(BACKOFF_SECONDS) - 1)]
                LOG.warning('HTTP %s em %s; nova tentativa em %ss.', response.status_code, path, wait)
                self.sleep(wait)
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
                if path == '/graphql' and payload.get('errors'):
                    raise RuntimeError('GraphQL retornou erros; resposta não armazenada.')
                if path == '/search/repositories' and payload.get('incomplete_results'):
                    if backoff_attempt >= self.max_retries:
                        raise RuntimeError('Busca incompleta após novas tentativas; resposta não armazenada.')
                    self.sleep(BACKOFF_SECONDS[min(backoff_attempt, len(BACKOFF_SECONDS) - 1)])
                    backoff_attempt += 1
                    continue
            self._save_cache(cache_path, payload, links)
            return payload, links

    def commit_dates(self, repository, shas):
        """Datas de autoria de até 100 commits por consulta GraphQL própria.

        Não consulta código nem usa biblioteca de acesso GitHub. Mantém a data
        commit.author.date, equivalente a authoredDate, e o SHA na evidência.
        """
        owner, repo = repository.split('/')
        results = {}
        unique = sorted(set(shas))
        if any(not re.fullmatch('[0-9a-fA-F]{40}', sha) for sha in unique):
            raise ValueError('SHA inválido para consulta de datas.')
        for offset in range(0, len(unique), 100):
            batch = unique[offset:offset + 100]
            fields = ' '.join(f'c{i}:object(expression:{json.dumps(sha)}){{... on Commit{{oid authoredDate}}}}'
                              for i, sha in enumerate(batch))
            query = 'query{repository(owner:' + json.dumps(owner) + ',name:' + json.dumps(repo) + '){' + fields + '}}'
            payload, _ = self.get('/graphql', {'query': query})
            data = payload['data']['repository']
            if data is None:
                raise RuntimeError('Repositório indisponível no GraphQL.')
            for i, sha in enumerate(batch):
                node = data[f'c{i}']
                if node is not None:
                    if node.get('oid') != sha or not node.get('authoredDate'):
                        raise RuntimeError('Commit GraphQL incompatível.')
                    results[sha] = {'sha': sha, 'commit': {'author': {'date': node['authoredDate']}}}
        return results

    def release_pages(self, repository):
        """Releases com notas e commit da tag, sem baixar metadados de assets."""
        owner, repo = repository.split('/')
        cursor, visited = None, set()
        while True:
            after = ',after:' + json.dumps(cursor) if cursor else ''
            query = ('query{repository(owner:' + json.dumps(owner) + ',name:' + json.dumps(repo) +
                     '){releases(first:100' + after + '){pageInfo{hasNextPage endCursor}'
                     'nodes{databaseId tagName publishedAt isDraft isPrerelease url description name '
                     'tagCommit{oid authoredDate}}}}}')
            payload, _ = self.get('/graphql', {'query': query})
            connection = payload['data']['repository']['releases']
            yield [{'id': r['databaseId'], 'tag_name': r['tagName'], 'published_at': r['publishedAt'],
                    'draft': r['isDraft'], 'prerelease': r['isPrerelease'], 'html_url': r['url'],
                    'body': r['description'], 'name': r['name'], '_tag_commit': r['tagCommit']}
                   for r in connection['nodes']]
            page = connection['pageInfo']
            if not page['hasNextPage']:
                return
            cursor = page['endCursor']
            if not cursor or cursor in visited:
                raise RuntimeError('Cursor inválido na paginação de releases.')
            visited.add(cursor)

    def ancestor_shas(self, repository, head_sha, targets, window_end, max_pages=100):
        """Provas positivas de ancestralidade pelo histórico do HEAD congelado.

        Ausência na busca limitada nunca prova divergência; o coletor usa compare
        REST para cada SHA que não for encontrado aqui.
        """
        owner, repo = repository.split('/')
        remaining, found, cursor = set(targets), set(), None
        for _ in range(max_pages):
            if not remaining:
                break
            after = ',after:' + json.dumps(cursor) if cursor else ''
            query = ('query{repository(owner:' + json.dumps(owner) + ',name:' + json.dumps(repo) +
                     '){object(oid:' + json.dumps(head_sha) + '){... on Commit{history(first:100,until:' +
                     json.dumps(window_end) + after + '){pageInfo{hasNextPage endCursor}nodes{oid}}}}}}')
            payload, _ = self.get('/graphql', {'query': query})
            connection = payload['data']['repository']['object']['history']
            page_shas = {n['oid'] for n in connection['nodes']}
            # Todos os SHAs observados são provas positivas, inclusive tags que
            # não têm release e serão verificadas posteriormente pelo coletor.
            found.update(page_shas)
            remaining.difference_update(page_shas)
            page = connection['pageInfo']
            if not page['hasNextPage']:
                break
            next_cursor = page['endCursor']
            if not next_cursor or next_cursor == cursor:
                raise RuntimeError('Cursor inválido no histórico do HEAD.')
            cursor = next_cursor
        return found
