"""Comando único de Tavares (#44): seleção + releases + runs + finalização.

Integra lab03.selection (#41), lab03.releases (#42) e lab03.runs (#43) com um
único transporte compartilhado (lab03.http.CachedTransport), repetindo a
ampliação de candidatos até comprovar o número de elegíveis exigido em
config['target_candidates'], ou falhando de forma explícita.
"""
from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
from pathlib import Path

from lab03 import releases, runs, selection, screening
from lab03.http import CachedTransport
from lab03.selection import ROOT, read_config

LOG = logging.getLogger(__name__)

TARGET_STEP = 50
MAX_PENDING_RETRIES = 3


def run(config, out, client):
    out = Path(out)
    attempt_config = dict(config)
    attempt = 0
    retries = 0
    while True:
        selection_dir = out / 'selection' if attempt == 0 else out / f'selection_expand_{attempt}'
        state = selection.collect(client, attempt_config, selection_dir)
        screened_dir = out / 'screening'
        _, candidates = screening.screen(client, state, screened_dir)
        LOG.info('Seleção (tentativa %s): %s candidatos pendentes de releases/runs.', attempt, len(candidates))
        releases.collect(client, attempt_config, candidates, out)
        runs.collect(client, attempt_config, candidates, out)
        for filename in ('releases_evidence.json', 'runs_evidence.json'):
            if not (out / filename).exists():
                selection.save_json(out / filename, {**{k: config[k] for k in ('window_start', 'window_end')},
                                                     'repositories': []})
        results = selection.finalize(screened_dir / 'selection_state.json',
                                     out / 'releases_evidence.json', out / 'runs_evidence.json',
                                     out / 'final_selection')
        eligible = sum(r['selection_status'] == 'eligible' for r in results)
        pending = sum(r['selection_status'] == 'pending_collectors' for r in results)
        LOG.info('Funil atual: %s elegíveis, %s pendentes, %s repositórios no total.',
                 eligible, pending, len(results))
        if eligible >= config['target_candidates']:
            return results
        if pending:
            retries += 1
            if retries > MAX_PENDING_RETRIES:
                raise RuntimeError(f'{pending} repositórios seguem pendentes após {retries} tentativas; '
                                   'inspecione releases_evidence.json/runs_evidence.json antes de repetir.')
            LOG.info('Ainda há pendências; repetindo a mesma seleção antes de ampliar.')
            continue
        retries = 0
        next_target = attempt_config['target_candidates'] + TARGET_STEP
        if next_target > attempt_config['max_search_results']:
            raise RuntimeError(
                f'Só {eligible} elegíveis entre {len(results)} examinados, com '
                f"{attempt_config['max_search_results']} como teto de uma busca única; ampliar mais "
                'exigiria fatiar a busca por faixa de estrelas, fora deste comando.')
        LOG.info('Só %s elegíveis; ampliando a seleção de %s para %s candidatos com Actions.',
                 eligible, attempt_config['target_candidates'], next_target)
        attempt_config = {**attempt_config, 'target_candidates': next_target}
        attempt += 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'lab03/config.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'lab03/data')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--transport', help='modulo:factory; factory() retorna get(path, params)')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s | %(message)s', datefmt='%H:%M:%S',
                        handlers=[logging.StreamHandler(sys.stdout)])
    logging.getLogger('lab03').setLevel(logging.DEBUG if args.verbose else logging.INFO)
    config = read_config(args.config)
    if args.transport:
        module, factory = args.transport.split(':', 1)
        client = getattr(importlib.import_module(module), factory)()
    else:
        client = CachedTransport(os.environ.get('GITHUB_TOKEN'))
    results = run(config, args.out, client)
    eligible = sum(r['selection_status'] == 'eligible' for r in results)
    print(f'{eligible} repositórios elegíveis de {len(results)} examinados; '
          f'ver {args.out / "final_selection"}.')
    return 0 if eligible >= config['target_candidates'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
