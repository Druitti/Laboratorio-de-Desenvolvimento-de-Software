"""Coleta REST de Santiago (#42), com transporte injetável de Tavares (#43)."""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import logging
import os
import re
import sys
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from lab03.metrics import lead_time
from lab03.selection import ROOT, RestTransport, read_config, save_json, timestamp, write_csv


LOG = logging.getLogger(__name__)


class IncompleteCollection(RuntimeError):
    """Não transformar erro ou truncamento em contagem zero."""


def export_checkpoint(out, config, evidence_name, metrics_name):
    """Preserva linhas ainda não revisitadas quando uma retomada é interrompida."""
    path = out / evidence_name
    evidence = []
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        if any(timestamp(previous[k]) != timestamp(config[k]) for k in ('window_start', 'window_end')):
            raise ValueError('Exportação anterior usa outra janela.')
        evidence = previous['repositories']
    path = out / metrics_name
    with path.open(encoding='utf-8', newline='') if path.exists() else open(os.devnull) as stream:
        metrics = list(csv.DictReader(stream))
    return evidence, metrics


def merged_rows(previous, current):
    rows = {r['repository']: r for r in previous}
    rows.update({r['repository']: r for r in current})
    return list(rows.values())


def is_404(error):
    response = getattr(error, 'response', None)
    return (getattr(response, 'status_code', None) == 404
            or getattr(error, 'status_code', None) == 404
            or bool(re.search(r'\bHTTP 404\b', str(error))))


def _item_count(payload):
    if isinstance(payload, list):
        return len(payload)
    for key in ('commits', 'workflow_runs'):
        if key in payload:
            return len(payload[key])
    return 0


def _matches_path(target_path, path):
    """Aceita tanto /repos/{owner}/{repo}/<resto> quanto a forma canônica que o
    GitHub às vezes usa no Link.next, /repositories/{id}/<resto>, desde que o
    <resto> (o que vem depois do repositório) seja exatamente o mesmo."""
    if target_path == path:
        return True
    match = re.fullmatch(r'/repos/[^/]+/[^/]+(/.*)', path)
    if not match:
        return False
    return bool(re.fullmatch(r'/repositories/\d+' + re.escape(match.group(1)), target_path))


def pages(client, path, params=None):
    """Segue os parâmetros de Link.next, mantendo chamadas relativas à API."""
    match = re.fullmatch(r'/repos/([^/]+/[^/]+)/releases', path)
    if match and not params and hasattr(client, 'release_pages'):
        yield from client.release_pages(match.group(1))
        return
    query = {'per_page': 100, 'page': 1, **(params or {})}
    visited = set()
    while True:
        signature = tuple(sorted((k, str(v)) for k, v in query.items()))
        if signature in visited:
            raise IncompleteCollection('Paginação cíclica.')
        visited.add(signature)
        LOG.info('GET %s | página %s: consultando...', path, query.get('page', 1))
        payload, links = client.get(path, query)
        LOG.info('GET %s | página %s: %s itens recebidos', path, query.get('page', 1), _item_count(payload))
        yield payload
        if 'next' not in links:
            return
        target = urlparse(links['next']['url'])
        if target.netloc != 'api.github.com' or target.scheme != 'https' or not _matches_path(target.path, path):
            raise IncompleteCollection('Link.next inesperado.')
        query = {**query, **{k: values[-1] for k, values in parse_qs(target.query).items()}}


def listing(client, path, identity):
    items = {}
    for payload in pages(client, path):
        if not isinstance(payload, list):
            raise IncompleteCollection('Resposta de listagem inválida.')
        for item in payload:
            items[item[identity]] = item
    return list(items.values())


def compare_commits(client, prefix, base, head):
    """Nunca usa o compare sem paginação (limite implícito de 250 commits)."""
    commits, expected, status = {}, None, None
    path = f'{prefix}/compare/{quote(base, safe="")}...{quote(head, safe="")}'
    for payload in pages(client, path):
        if expected is None:
            expected, status = payload['total_commits'], payload['status']
        elif expected != payload['total_commits'] or status != payload['status']:
            raise IncompleteCollection('Comparação mudou durante a paginação.')
        for commit in payload['commits']:
            commits[commit['sha']] = compact_commit(commit)
    if len(commits) != expected:
        raise IncompleteCollection('Compare truncado: contagem difere de total_commits.')
    return list(commits.values()), status


def compact_commit(commit):
    """Campos usados nas métricas/validação; respostas integrais ficam no cache."""
    result = {'sha': commit['sha'], 'commit': {'author': commit['commit']['author']}}
    for key in ('message', 'committer'):
        if key in commit['commit']:
            result['commit'][key] = commit['commit'][key]
    if 'html_url' in commit:
        result['html_url'] = commit['html_url']
    return result


def collect_repository(client, candidate, config):
    name, branch = candidate['repository'], candidate['default_branch']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name) or any(part in ('.', '..') for part in name.split('/')):
        raise ValueError('Nome de repositório inválido.')
    start, end = timestamp(config['window_start']), timestamp(config['window_end'])
    prefix = f'/repos/{name}'
    LOG.info('%s | identificando HEAD do branch %s...', name, branch)
    branch_commit, _ = client.get(f'{prefix}/commits/{quote(branch, safe="")}')
    branch_sha = branch_commit['sha']  # Fixar o HEAD evita alterações durante esta coleta.
    raw = {'repository': name, 'default_branch': branch, 'branch_sha': branch_sha,
           'window_start': config['window_start'], 'window_end': config['window_end'],
           'collected_at': datetime.now(timezone.utc).isoformat(),
           'releases': [], 'tags': [], 'comparisons': {}, 'metrics': {}}
    resolved, ancestry = {}, {}

    def resolve(ref):
        if ref not in resolved:
            LOG.debug('%s | resolvendo commit %s...', name, ref)
            resolved[ref], _ = client.get(f'{prefix}/commits/{quote(ref, safe="")}')
            resolved[resolved[ref]['sha']] = resolved[ref]
        return resolved[ref]

    def belongs(sha):
        if sha not in ancestry:
            LOG.debug('%s | verificando ancestralidade de %s...', name, sha)
            result, _ = client.get(f'{prefix}/compare/{quote(sha, safe="")}...{branch_sha}',
                                   {'per_page': 1, 'page': 1})
            ancestry[sha] = {'status': result['status'],
                             'on_default_branch': result['status'] in ('ahead', 'identical')}
        return ancestry[sha]

    # published_at, não a ordem de retorno da API, determina o predecessor.
    LOG.info('%s | listando releases e pré-releases...', name)
    releases = listing(client, f'{prefix}/releases', 'id')
    for release in releases:
        tag_commit = release.get('_tag_commit')
        if tag_commit:
            commit = {'sha': tag_commit['oid'], 'commit': {'author': {'date': tag_commit['authoredDate']}}}
            resolved[release['tag_name']] = commit
            resolved[commit['sha']] = commit
    # Só a antecessora mais recente de cada série é contexto necessário.
    # A API ordena por criação, não por published_at; ordenar localmente é obrigatório.
    try:
        releases.sort(key=lambda r: (timestamp(r['published_at']) if not r['draft']
                                    else start, r['id']), reverse=True)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise IncompleteCollection('Release publicada sem data válida.') from error
    if hasattr(client, 'ancestor_shas'):
        targets = {r['_tag_commit']['oid'] for r in releases if r.get('_tag_commit') and not r['draft']
                   and start <= timestamp(r['published_at']) < end}
        for sha in client.ancestor_shas(name, branch_sha, targets, config['window_end']):
            ancestry[sha] = {'status': 'identical' if sha == branch_sha else 'ahead',
                             'on_default_branch': True, 'proof': 'frozen_head_history'}
    context_stable = context_any = False
    LOG.info('%s | %s releases encontradas; aplicando filtros...', name, len(releases))
    for position, release in enumerate(releases, 1):
        LOG.info('%s | release %s/%s: %s', name, position, len(releases), release['tag_name'])
        record = {'release': release, 'status': 'draft' if release['draft'] else 'pending'}
        raw['releases'].append(record)
        if release['draft']:
            continue
        try:
            published = timestamp(release['published_at'])
        except (ValueError, TypeError, AttributeError):
            raise IncompleteCollection('Release publicada sem data válida.')
        if published >= end:
            record['status'] = 'after_window'
            continue
        if published < start and context_any and (release['prerelease'] or context_stable):
            record['status'] = 'older_than_required_context'
            continue
        try:
            commit = resolve(release['tag_name'])
            record.update(commit_sha=commit['sha'], author_date=commit['commit']['author']['date'],
                          **belongs(commit['sha']))
        except Exception as error:
            if not is_404(error):
                raise
            # Tag apagada: não há prova de branch nem contagem completa.
            LOG.warning('%s | release %s sem prova de branch: HTTP 404', name, release['tag_name'])
            record['status'] = 'unresolved_404'
            continue
        record['status'] = ('in_window' if published >= start else 'before_window')
        if published < start and record.get('on_default_branch'):
            context_any = True
            if not release['prerelease']:
                context_stable = True

    LOG.info('%s | listando tags e datas dos commits...', name)
    tags = listing(client, f'{prefix}/tags', 'name')
    if hasattr(client, 'commit_dates'):
        missing = [tag['commit']['sha'] for tag in tags if tag['commit']['sha'] not in resolved]
        resolved.update(client.commit_dates(name, missing))
    for position, tag in enumerate(tags, 1):
        LOG.info('%s | tag %s/%s: %s', name, position, len(tags), tag['name'])
        try:
            commit = resolve(tag['commit']['sha'])
            date = timestamp(commit['commit']['author']['date'])
            in_window = start <= date < end
            raw['tags'].append({'tag': tag, 'commit_sha': commit['sha'],
                                'author_date': commit['commit']['author']['date'],
                                'in_window': in_window,
                                **(belongs(commit['sha']) if in_window else
                                   {'on_default_branch': None, 'status': 'outside_window'})})
        except Exception as error:
            if not is_404(error):
                raise
            LOG.warning('%s | tag %s não resolvida: HTTP 404', name, tag['name'])
            raw['tags'].append({'tag': tag, 'status': 'unresolved_404',
                                'in_window': None, 'on_default_branch': None})

    # Duas séries preservam as variantes para RQ07, sem executar análise da S03.
    for variant, include_pre in [('stable', False), ('with_prereleases', True)]:
        series = [r for r in raw['releases']
                  if r.get('on_default_branch') and r['status'] in ('in_window', 'before_window')
                  and (include_pre or not r['release']['prerelease'])]
        series.sort(key=lambda r: (timestamp(r['release']['published_at']), r['release']['id']))
        LOG.info('%s | variante %s: %s releases na série (inclui contexto)', name, variant, len(series))
        intervals = []
        for index, record in enumerate(series):
            if record['status'] != 'in_window':
                continue
            release = record['release']
            interval = {'release_id': release['id'], 'head_tag': release['tag_name'],
                        'published_at': release['published_at'], 'base_tag': None,
                        'status': 'no_previous_release', 'commits': []}
            if index:
                previous = series[index - 1]
                interval['base_tag'] = previous['release']['tag_name']
                LOG.info('%s | %s: comparando %s → %s...', name, variant, interval['base_tag'], interval['head_tag'])
                try:
                    commits, comparison_status = compare_commits(
                        client, prefix, previous['commit_sha'], record['commit_sha'])
                    interval.update(commits=commits, compare_status=comparison_status,
                                    status='ok' if comparison_status in ('ahead', 'identical')
                                    else 'non_forward_history')
                except Exception as error:
                    if not is_404(error):
                        raise
                    LOG.warning('%s | comparação %s → %s ignorada: HTTP 404', name, interval['base_tag'], interval['head_tag'])
                    interval['status'] = 'compare_404'
            intervals.append(interval)
        raw['comparisons'][variant] = intervals
        raw['metrics'][variant] = lead_time(intervals)
        LOG.info('%s | %s: lead time calculado; %s intervalos válidos, %s ignorados',
                 name, variant, raw['metrics'][variant]['measured_releases'],
                 raw['metrics'][variant]['ignored_releases'])
    unresolved = sum(r['status'] == 'unresolved_404' for r in raw['releases'])
    unresolved_tags = sum(t.get('status') == 'unresolved_404' for t in raw['tags'])
    raw['unresolved_tags'] = unresolved_tags
    raw['complete'] = unresolved == 0 and unresolved_tags == 0
    raw['stable_releases'] = sum(r.get('on_default_branch', False)
                                 and r['status'] == 'in_window' and not r['release']['prerelease']
                                 for r in raw['releases']) if raw['complete'] else None
    raw['unresolved_release_tags'] = unresolved
    return raw


def collect(client, config, candidates, out):
    """Chamável no pipeline único de #44; cada repositório é um checkpoint."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    previous_evidence, previous_metrics = export_checkpoint(out, config, 'releases_evidence.json', 'lead_time.csv')
    evidence, metrics = [], []
    seen = set()
    candidates = list(candidates)
    started = perf_counter()
    LOG.info('Iniciando coleta de %s repositórios | janela %s até %s (fim exclusivo) | saída %s',
             len(candidates), config['window_start'], config['window_end'], out)
    for position, candidate in enumerate(candidates, 1):
        repo_started = perf_counter()
        name = candidate['repository']
        LOG.info('[%s/%s] %s | iniciando', position, len(candidates), name)
        if name in seen:
            raise ValueError('Candidato duplicado.')
        seen.add(name)
        path = out / 'raw' / name / 'releases.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raw = json.loads(path.read_text(encoding='utf-8'))
            if any(raw[k] != config[k] for k in ('window_start', 'window_end')) or raw['default_branch'] != candidate['default_branch']:
                raise ValueError('Checkpoint de janela/branch diferente; use outra saída.')
        else:
            raw = {'complete': False}
        if raw['complete']:
            for intervals in raw.get('comparisons', {}).values():
                for interval in intervals:
                    interval['commits'] = [compact_commit(c) for c in interval['commits']]
            save_json(path, raw)
            LOG.info('%s | checkpoint completo reutilizado; sem novas consultas', name)
        else:
            LOG.info('%s | coletando dados (novo ou pendente)...', name)
            try:
                raw = collect_repository(client, candidate, config)
            except Exception as error:
                status = getattr(getattr(error, 'response', None), 'status_code', None)
                if status is None:
                    match = re.search(r'\bHTTP (\d{3})\b', str(error))
                    status = match.group(1) if match else None
                LOG.error('%s | coleta pendente: %s%s', name, type(error).__name__,
                          f' (HTTP {status})' if status else '')
                # Mensagens do transporte podem conter URLs sensíveis: guardar só a classe.
                raw = {**{k: config[k] for k in ('window_start', 'window_end')},
                       'repository': name, 'default_branch': candidate['default_branch'],
                       'complete': False, 'stable_releases': None,
                       'error_type': type(error).__name__}
            save_json(path, raw)
        count = raw.get('stable_releases')
        evidence.append({'repository': name, 'default_branch': candidate['default_branch'],
                         'complete': raw['complete'], 'stable_releases': count,
                         'evidence_path': str(path), 'error_type': raw.get('error_type')})
        stable = raw.get('metrics', {}).get('stable', {})
        metrics.append({'repository': name, 'complete': raw['complete'], 'stable_releases': count,
                        **{k: stable.get(k) for k in ('lead_time_release_hours', 'lead_time_commit_hours',
                                                     'measured_releases', 'measured_commit_inclusions', 'ignored_releases')}})
        envelope = {**{k: config[k] for k in ('window_start', 'window_end')},
                    'repositories': merged_rows(previous_evidence, evidence)}
        save_json(out / 'releases_evidence.json', envelope)
        write_csv(out / 'lead_time.csv', merged_rows(previous_metrics, metrics), list(metrics[0]))
        LOG.info('[%s/%s] %s | %s | releases principais: %s | %.1fs | evidências salvas',
                 position, len(candidates), name, 'concluído' if raw['complete'] else 'pendente',
                 count if count is not None else 'desconhecido', perf_counter() - repo_started)
    LOG.info('Coleta encerrada em %.1fs | completos: %s | pendentes: %s',
             perf_counter() - started, sum(row['complete'] for row in evidence),
             sum(not row['complete'] for row in evidence))
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description='Releases e lead time — Santiago, issue #42')
    parser.add_argument('--config', type=Path, default=ROOT / 'lab03/config.json')
    parser.add_argument('--candidates', type=Path, default=ROOT / 'lab03/data/selection/candidates.csv')
    parser.add_argument('--out', type=Path, default=ROOT / 'lab03/data')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--verbose', action='store_true', help='Mostrar também resolução de commits e provas de ancestralidade')
    parser.add_argument('--transport', help='modulo:factory; factory() retorna get(path, params)')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s | %(message)s', datefmt='%H:%M:%S',
                        handlers=[logging.StreamHandler(sys.stdout)])
    LOG.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    config = read_config(args.config)
    with args.candidates.open(encoding='utf-8', newline='') as stream:
        candidates = list(csv.DictReader(stream))
    if args.limit is not None:
        if args.limit <= 0:
            parser.error('--limit deve ser positivo.')
        candidates = candidates[:args.limit]
    if not candidates:
        parser.error('Nenhum candidato disponível.')
    if args.transport:
        module, factory = args.transport.split(':', 1)
        client = getattr(importlib.import_module(module), factory)()
    else:
        client = RestTransport(os.environ.get('GITHUB_TOKEN'))
    evidence = collect(client, config, candidates, args.out)
    pending = sum(not row['complete'] for row in evidence)
    print(f'{len(evidence)} repositórios processados; {pending} pendentes. Não comprova elegibilidade de runs.')
    return 1 if pending else 0


if __name__ == '__main__':
    raise SystemExit(main())
