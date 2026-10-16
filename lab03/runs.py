"""Coleta de workflow runs, CFR(a) e recuperação de Tavares (#43)."""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

from lab03.metrics import change_failure_rate, recovery_episodes
from lab03.releases import IncompleteCollection, pages
from lab03.selection import ROOT, read_config, save_json, timestamp, write_csv

LOG = logging.getLogger(__name__)

MIN_SUBDIVISION = timedelta(seconds=2)


def month_ranges(start, end):
    """Sub-janelas mensais [início, fim), fim exclusivo, dentro de [start, end)."""
    current = start.replace(day=1)
    while current < end:
        year = current.year + (current.month == 12)
        month = current.month % 12 + 1
        following = current.replace(year=year, month=month)
        yield max(current, start), min(following, end)
        current = following


def created_qualifier(start, end):
    # O qualificador created do GitHub é inclusivo nos dois extremos.
    inclusive_end = end - timedelta(seconds=1)
    return f'{start.isoformat()}..{inclusive_end.isoformat()}'


def fetch_window(client, prefix, branch, start, end, runs):
    """Busca runs de [start, end), subdividindo recursivamente acima de 1000."""
    params = {'branch': branch, 'event': 'push', 'created': created_qualifier(start, end)}
    pages_iterator = pages(client, f'{prefix}/actions/runs', params)
    first = next(pages_iterator, None)
    if first is None:
        return
    total = first['total_count']
    if total > 1000:
        if end - start <= MIN_SUBDIVISION:
            raise IncompleteCollection('Mais de 1000 runs em uma janela mínima; não subdivisível.')
        mid = start + (end - start) / 2
        LOG.info('%s | %s..%s: %s runs (>1000), subdividindo em %s..%s e %s..%s',
                 prefix, start, end, total, start, mid, mid, end)
        fetch_window(client, prefix, branch, start, mid, runs)
        fetch_window(client, prefix, branch, mid, end, runs)
        return
    for run in first['workflow_runs']:
        runs[run['id']] = run
    for payload in pages_iterator:
        if payload['total_count'] != total:
            raise IncompleteCollection('Contagem de runs mudou durante a paginação.')
        for run in payload['workflow_runs']:
            runs[run['id']] = run


def collect_repository(client, candidate, config):
    name, branch = candidate['repository'], candidate['default_branch']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name) or any(part in ('.', '..') for part in name.split('/')):
        raise ValueError('Nome de repositório inválido.')
    start, end = timestamp(config['window_start']), timestamp(config['window_end'])
    prefix = f'/repos/{name}'
    runs = {}
    for month_start, month_end in month_ranges(start, end):
        LOG.info('%s | mês %s a %s (fim exclusivo)...', name, month_start.date(), month_end.date())
        fetch_window(client, prefix, branch, month_start, month_end, runs)
    classified = list(runs.values())
    cfr = change_failure_rate(classified)
    recovery = recovery_episodes(classified)
    return {'repository': name, 'default_branch': branch,
            'window_start': config['window_start'], 'window_end': config['window_end'],
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'runs': classified, 'complete': True,
            'valid_runs': cfr['failures'] + cfr['successes'],
            'cfr': cfr, 'recovery': recovery}


def collect(client, config, candidates, out):
    """Chamável no pipeline único de #44; cada repositório é um checkpoint."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    evidence, metrics_rows = [], []
    seen = set()
    candidates = list(candidates)
    started = perf_counter()
    LOG.info('Iniciando coleta de runs de %s repositórios | janela %s até %s (fim exclusivo) | saída %s',
             len(candidates), config['window_start'], config['window_end'], out)
    for position, candidate in enumerate(candidates, 1):
        repo_started = perf_counter()
        name = candidate['repository']
        LOG.info('[%s/%s] %s | iniciando', position, len(candidates), name)
        if name in seen:
            raise ValueError('Candidato duplicado.')
        seen.add(name)
        path = out / 'raw' / name / 'runs.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raw = json.loads(path.read_text(encoding='utf-8'))
            if any(raw[k] != config[k] for k in ('window_start', 'window_end')) or raw['default_branch'] != candidate['default_branch']:
                raise ValueError('Checkpoint de janela/branch diferente; use outra saída.')
        else:
            raw = {'complete': False}
        if raw['complete']:
            LOG.info('%s | checkpoint completo reutilizado; sem novas consultas', name)
        else:
            try:
                raw = collect_repository(client, candidate, config)
            except Exception as error:
                status = getattr(getattr(error, 'response', None), 'status_code', None)
                if status is None:
                    match = re.search(r'\bHTTP (\d{3})\b', str(error))
                    status = match.group(1) if match else None
                LOG.error('%s | coleta pendente: %s%s', name, type(error).__name__,
                          f' (HTTP {status})' if status else '')
                raw = {**{k: config[k] for k in ('window_start', 'window_end')},
                       'repository': name, 'default_branch': candidate['default_branch'],
                       'complete': False, 'valid_runs': None,
                       'error_type': type(error).__name__}
            save_json(path, raw)
        count = raw.get('valid_runs')
        evidence.append({'repository': name, 'default_branch': candidate['default_branch'],
                         'complete': raw['complete'], 'valid_runs': count,
                         'evidence_path': str(path), 'error_type': raw.get('error_type')})
        cfr = raw.get('cfr', {})
        recovery = raw.get('recovery', {})
        metrics_rows.append({'repository': name, 'complete': raw['complete'], 'valid_runs': count,
                             'cfr_ci': cfr.get('cfr_ci'), 'cfr_failures': cfr.get('failures'),
                             'cfr_successes': cfr.get('successes'),
                             'recovery_hours': recovery.get('recovery_hours'),
                             'recovery_episodes': recovery.get('episodes'),
                             'recovery_censored': recovery.get('censored'),
                             'recovery_censored_ratio': recovery.get('censored_ratio')})
        envelope = {**{k: config[k] for k in ('window_start', 'window_end')}, 'repositories': evidence}
        save_json(out / 'runs_evidence.json', envelope)
        write_csv(out / 'cfr_recovery.csv', metrics_rows, list(metrics_rows[0]))
        LOG.info('[%s/%s] %s | %s | runs válidos: %s | %.1fs | evidências salvas',
                 position, len(candidates), name, 'concluído' if raw['complete'] else 'pendente',
                 count if count is not None else 'desconhecido', perf_counter() - repo_started)
    LOG.info('Coleta encerrada em %.1fs | completos: %s | pendentes: %s',
             perf_counter() - started, sum(row['complete'] for row in evidence),
             sum(not row['complete'] for row in evidence))
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description='Workflow runs, CFR(a) e recuperação — Tavares, issue #43')
    parser.add_argument('--config', type=Path, default=ROOT / 'lab03/config.json')
    parser.add_argument('--candidates', type=Path, default=ROOT / 'lab03/data/selection/candidates.csv')
    parser.add_argument('--out', type=Path, default=ROOT / 'lab03/data')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--verbose', action='store_true')
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
        from lab03.http import CachedTransport
        client = CachedTransport(os.environ.get('GITHUB_TOKEN'))
    evidence = collect(client, config, candidates, args.out)
    pending = sum(not row['complete'] for row in evidence)
    print(f'{len(evidence)} repositórios processados; {pending} pendentes. Não comprova elegibilidade de releases.')
    return 1 if pending else 0


if __name__ == '__main__':
    raise SystemExit(main())
