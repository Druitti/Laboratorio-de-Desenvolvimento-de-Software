"""Seleção, metadados e funil de Ferreira (#41), sem coletores de releases/runs."""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import requests

ROOT = Path(__file__).resolve().parents[1]
API = 'https://api.github.com'
FIELDS = ['repository', 'repository_id', 'default_branch', 'stars', 'language',
          'contributors', 'contributors_status', 'created_at', 'age_days_at_window_end', 'workflows',
          'collected_at', 'selection_status']


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Datas devem incluir timezone.')
    return result.astimezone(timezone.utc)


def read_config(path):
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    start, end = timestamp(config['window_start']), timestamp(config['window_end'])
    if start >= end:
        raise ValueError('A janela deve ter início anterior ao fim exclusivo.')
    for key in ('target_candidates', 'max_search_results', 'min_stars', 'min_releases', 'min_valid_runs'):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f'{key} deve ser inteiro positivo.')
    if config['target_candidates'] > config['max_search_results']:
        raise ValueError('target_candidates não pode superar max_search_results.')
    return config


class Transport(Protocol):
    def get(self, path: str, params: dict | None = None) -> tuple[object, dict]: ...


class ContributorsUnavailable(RuntimeError):
    """Limitação explícita do GitHub para históricos grandes, não rate limit."""


class RestTransport:
    """Transporte mínimo de metadados; cache/rate limit compartilhados pertencem a #43."""
    def __init__(self, token):
        if not token:
            raise ValueError('Defina GITHUB_TOKEN no ambiente.')
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {token}',
                                     'Accept': 'application/vnd.github+json',
                                     'X-GitHub-Api-Version': '2022-11-28'})

    def get(self, path, params=None):
        # Não aceita URLs externas nem imprime cabeçalhos/credenciais.
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Endpoint precisa ser um caminho relativo à API GitHub.')
        response = self.session.get(API + path, params=params, timeout=45)
        if response.status_code == 204:
            return [], response.links
        if response.status_code != 200:
            if (response.status_code == 403 and path.endswith('/contributors')
                    and 'too large to list contributors' in response.json().get('message', '')):
                raise ContributorsUnavailable(path)
            raise RuntimeError(f'HTTP {response.status_code} em {path}; '
                               'retome após resolver acesso/cota. Nenhum erro é contado como ausência.')
        return response.json(), response.links


def _search_range(client, config, low, high, end_date):
    """Busca uma faixa de estrelas [low, high] (high=None é aberta para cima).

    Retorna os itens da faixa e, se a faixa estourar o teto de 1000 resultados
    de uma única busca, a contagem de estrelas do último item obtido — sinal de
    que a faixa precisa ser dividida em `search_candidates`.
    """
    stars = f'stars:{low}..{high}' if high is not None else f'stars:>{low - 1}'
    query = f'{stars} created:<{end_date} fork:false archived:false'
    items = []
    page = 1
    while True:
        payload, links = client.get('/search/repositories',
                                    {'q': query, 'sort': 'stars', 'order': 'desc',
                                     'per_page': 100, 'page': page})
        if payload.get('incomplete_results'):
            raise RuntimeError('Busca incompleta; tente novamente ou use faixas menores.')
        items.extend(payload['items'])
        if 'next' not in links or not payload['items']:
            return items, None
        page += 1
        if page > 10:
            return items, items[-1]['stargazers_count']


def search_candidates(client, config):
    # Metadados de popularidade são atuais; criação precede o fim da janela.
    # O teto de 1000 resultados é por consulta, não pelo total da amostra: uma
    # faixa que estoura é dividida por estrelas e cada parte é buscada de novo.
    end_date = timestamp(config['window_end']).date().isoformat()
    seen = set()
    ranges = [(config['min_stars'] + 1, None)]
    while ranges and len(seen) < config['max_search_results']:
        low, high = ranges.pop(0)
        items, boundary = _search_range(client, config, low, high, end_date)
        if boundary is not None:
            if high is not None and boundary >= high:
                raise RuntimeError(
                    f'Mais de 1000 repositórios com stars={boundary}; particionar por '
                    'estrelas não resolve este caso, refine o critério de amostragem.')
            # Itens com stars > boundary já estão totalmente cobertos pelas 10
            # páginas obtidas; os demais (incluindo possíveis empates no limite)
            # ficam para a faixa [low, boundary], buscada na próxima iteração.
            ranges.insert(0, (low, boundary))
            items = [item for item in items if item['stargazers_count'] > boundary]
        for item in items:
            if item['id'] in seen:
                continue
            seen.add(item['id'])
            yield item
            if len(seen) >= config['max_search_results']:
                return


def metadata(client, candidate, config, collected_at):
    name = candidate['full_name']
    repo, _ = client.get(f'/repos/{name}')
    created = timestamp(repo['created_at'])
    end = timestamp(config['window_end'])
    row = dict(repository=repo['full_name'], repository_id=repo['id'],
               default_branch=repo['default_branch'], stars=repo['stargazers_count'],
               language=repo['language'] or '', contributors='', contributors_status='not_collected',
               created_at=repo['created_at'],
               age_days_at_window_end=round((end - created).total_seconds() / 86400, 4),
               workflows='', collected_at=collected_at, selection_status='pending_collectors')
    if repo['fork'] or repo['archived'] or repo['stargazers_count'] <= config['min_stars'] or created >= end:
        row['selection_status'] = 'excluded_metadata'
        return row
    workflows, _ = client.get(f'/repos/{name}/actions/workflows', {'per_page': 1})
    row['workflows'] = workflows['total_count']
    if row['workflows'] == 0:
        row['selection_status'] = 'excluded_no_actions'
        return row
    try:
        people, links = client.get(f'/repos/{name}/contributors', {'per_page': 1, 'anon': 'true'})
    except ContributorsUnavailable:
        row['contributors_status'] = 'unavailable_large_history'
        return row
    if 'last' in links:
        from urllib.parse import parse_qs, urlparse
        row['contributors'] = int(parse_qs(urlparse(links['last']['url']).query)['page'][0])
    elif 'next' in links:
        raise RuntimeError('Contagem de contribuidores sem última página; não estimar contagem.')
    else:
        row['contributors'] = len(people)
    row['contributors_status'] = 'measured'
    return row


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def save_json(path, value, sleep=time.sleep, attempts=5):
    # No Windows, um antivírus/indexador pode segurar o arquivo por um instante;
    # a troca atômica é breve o bastante para valer uma nova tentativa curta.
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for attempt in range(attempts):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            sleep(0.2 * (attempt + 1))


def export_selection(out, state):
    rows = state['repositories']
    selected = [r for r in rows if r['selection_status'] == 'pending_collectors']
    write_csv(out / 'metadata.csv', rows, FIELDS)
    write_csv(out / 'candidates.csv', selected, FIELDS)
    counts = [{'stage': 'examined', 'count': len(rows)},
              {'stage': 'excluded_metadata', 'count': sum(r['selection_status'] == 'excluded_metadata' for r in rows)},
              {'stage': 'excluded_no_actions', 'count': sum(r['selection_status'] == 'excluded_no_actions' for r in rows)},
              {'stage': 'pending_collectors', 'count': len(selected)},
              {'stage': 'eligible', 'count': 0}]
    write_csv(out / 'funnel.csv', counts, ['stage', 'count'])


def collect(client, config, out):
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = out / 'selection_state.json'
    state = json.loads(checkpoint.read_text()) if checkpoint.exists() else {
        'config': config, 'started_at': datetime.now(timezone.utc).isoformat(), 'repositories': []}
    if state['config'] != config:
        raise ValueError('Checkpoint usa outra configuração; escolha nova pasta de saída.')
    for row in state['repositories']:
        row.setdefault('contributors_status', 'measured' if row['contributors'] != '' else 'not_collected')
    seen = {r['repository_id'] for r in state['repositories']}
    selected = sum(r['selection_status'] == 'pending_collectors' for r in state['repositories'])
    if selected < config['target_candidates']:
        for candidate in search_candidates(client, config):
            if candidate['id'] in seen:
                continue
            row = metadata(client, candidate, config, datetime.now(timezone.utc).isoformat())
            seen.add(row['repository_id'])
            state['repositories'].append(row)
            selected += row['selection_status'] == 'pending_collectors'
            save_json(checkpoint, state)
            export_selection(out, state)
            print(f"{selected}/{config['target_candidates']} candidatos com Actions; {row['repository']}", flush=True)
            if selected >= config['target_candidates']:
                break
    export_selection(out, state)
    if selected < config['target_candidates']:
        raise RuntimeError(f'Só {selected} candidatos; busca limitada/exaurida. Não é amostra completa.')
    return state


def read_evidence(path, config, count_field):
    payload = json.loads(path.read_text())
    for key in ('window_start', 'window_end'):
        if timestamp(payload[key]) != timestamp(config[key]):
            raise ValueError('Evidência usa janela diferente da seleção.')
    result = {}
    for r in payload['repositories']:
        if r['repository'] in result:
            raise ValueError('Evidência duplicada por repositório.')
        if type(r['complete']) is not bool:
            raise ValueError('complete deve ser booleano.')
        if not (not r['complete'] and r[count_field] is None) and (type(r[count_field]) is not int or r[count_field] < 0):
            raise ValueError('Contagem inválida na evidência.')
        if not r.get('evidence_path'):
            raise ValueError('Falta referência ao artefato bruto da coleta.')
        result[r['repository']] = r
    return result


def finalize(state_path, releases_path, runs_path, out):
    state = json.loads(state_path.read_text())
    config = state['config']
    releases = read_evidence(releases_path, config, 'stable_releases')
    runs = read_evidence(runs_path, config, 'valid_runs')
    results = []
    for r in state['repositories']:
        status = r['selection_status']
        a, b = releases.get(r['repository']), runs.get(r['repository'])
        if status == 'pending_collectors':
            if not a or not b or not a['complete'] or not b['complete']:
                status = 'pending_collectors'
            elif any(x['default_branch'] != r['default_branch'] for x in (a, b)):
                raise ValueError('Default branch diverge entre seleção e coletores.')
            elif a['stable_releases'] < config['min_releases']:
                status = 'excluded_releases'
            elif b['valid_runs'] < config['min_valid_runs']:
                status = 'excluded_runs'
            else:
                status = 'eligible'
        results.append({**r, 'selection_status': status})
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / 'selection.csv', results, FIELDS)
    write_csv(out / 'eligible.csv', [r for r in results if r['selection_status'] == 'eligible'], FIELDS)
    stages = ['excluded_metadata', 'excluded_no_actions', 'excluded_releases', 'excluded_runs', 'pending_collectors', 'eligible']
    write_csv(out / 'funnel.csv', [{'stage': 'examined', 'count': len(results)}] +
              [{'stage': s, 'count': sum(r['selection_status'] == s for r in results)} for s in stages], ['stage', 'count'])
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--config', type=Path, default=ROOT / 'lab03/config.json')
    c.add_argument('--out', type=Path, default=ROOT / 'lab03/data/selection')
    f = sub.add_parser('finalize')
    f.add_argument('--state', type=Path, required=True)
    f.add_argument('--releases', type=Path, required=True)
    f.add_argument('--runs', type=Path, required=True)
    f.add_argument('--out', type=Path, default=ROOT / 'lab03/data/final_selection')
    args = parser.parse_args()
    if args.command == 'collect':
        collect(RestTransport(os.getenv('GITHUB_TOKEN')), read_config(args.config), args.out)
    else:
        finalize(args.state, args.releases, args.runs, args.out)


if __name__ == '__main__':
    main()
