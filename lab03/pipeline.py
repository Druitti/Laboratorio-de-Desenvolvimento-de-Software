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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from lab03 import releases, runs, selection, screening
from lab03.http import CachedTransport
from lab03.selection import ROOT, read_config

LOG = logging.getLogger(__name__)

TARGET_STEP = 500
MAX_PENDING_RETRIES = 3
CACHE_PRUNE_BYTES = 512 * 1024 ** 2  # disco observado com pouca folga (#50); poda cedo em vez de arriscar.
MAX_WORKERS = 4  # #50: 8 workers disparou um limite secundário (anti-abuso) silencioso de ~1h;
# a cota primária (X-RateLimit-*) sobra, mas threads demais em paralelo parecem acionar
# o rate limit secundário do GitHub, que não aparece nos cabeçalhos de cota. Reduzido
# após observar essa pausa em execução real; reavaliar com o log de espera agora visível.


def _prune_cache(client, max_bytes=CACHE_PRUNE_BYTES):
    # Só CachedTransport sabe podar o próprio cache; o transporte injetável dos
    # testes (ou de --transport) pode não ter o método.
    prune = getattr(client, 'prune_cache', None)
    if prune is not None and prune(max_bytes):
        LOG.info('Cache HTTP podado: excedeu %s bytes; raw/evidências já concluídos não são afetados.', max_bytes)


def _process_candidate(client, attempt_config, candidate, out, releases_lock, runs_lock):
    # releases.collect/runs.collect buscam a rede sem lock; só a leitura+mescla+
    # escrita do envelope compartilhado (releases_evidence.json/runs_evidence.json)
    # é serializada, para que candidatos concorrentes não percam entradas um do outro.
    releases.collect(client, attempt_config, [candidate], out, lock=releases_lock)
    runs.collect(client, attempt_config, [candidate], out, lock=runs_lock)


def run(config, out, client, max_workers=MAX_WORKERS):
    out = Path(out)
    attempt_config = dict(config)
    attempt = 0
    retries = 0
    pending = 0
    while True:
        selection_dir = out / 'selection' if attempt == 0 else out / f'selection_expand_{attempt}'
        try:
            state = selection.collect(client, attempt_config, selection_dir)
        except RuntimeError as error:
            if pending:
                raise RuntimeError(f'{pending} repositórios seguem pendentes; busca de novos candidatos esgotada.') from error
            raise
        screened_dir = out / 'screening'
        _, candidates = screening.screen(client, state, screened_dir)
        LOG.info('Seleção (tentativa %s): %s candidatos pendentes de releases/runs.', attempt, len(candidates))
        for filename in ('releases_evidence.json', 'runs_evidence.json'):
            if not (out / filename).exists():
                selection.save_json(out / filename, {**{k: config[k] for k in ('window_start', 'window_end')},
                                                     'repositories': []})
        # Candidatos são processados em paralelo (releases+runs por repositório);
        # funil incremental: uma interrupção não oculta repositórios já
        # comprovados enquanto os demais coletores ainda trabalham.
        releases_lock, runs_lock = threading.Lock(), threading.Lock()
        early_exit = None
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process_candidate, client, attempt_config, candidate, out,
                                   releases_lock, runs_lock): candidate for candidate in candidates}
            for future in as_completed(futures):
                future.result()
                _prune_cache(client)
                # Ler os dois arquivos compartilhados exige os mesmos locks dos
                # escritores: no Windows, ler um arquivo no instante exato em que
                # outro thread troca seu .tmp por ele (save_json) derruba com
                # PermissionError — reproduzido de forma intermitente em teste
                # com 10 candidatos concorrentes antes desta correção.
                with releases_lock, runs_lock:
                    partial = selection.finalize(screened_dir / 'selection_state.json',
                                                 out / 'releases_evidence.json', out / 'runs_evidence.json',
                                                 out / 'final_selection')
                if sum(r['selection_status'] == 'eligible' for r in partial) >= config['target_candidates']:
                    early_exit = partial
                    # Não espera os candidatos ainda não iniciados; os já em
                    # andamento (no máximo max_workers) ainda terminam e salvam
                    # suas evidências, nunca são interrompidos a meio da escrita.
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
        if early_exit is not None:
            return early_exit
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
            if retries <= MAX_PENDING_RETRIES:
                LOG.info('Ainda há pendências; repetindo a mesma seleção antes de ampliar.')
                continue
            LOG.info('Pendências preservadas no funil; buscando outros candidatos sem contá-las como elegíveis.')
        retries = 0
        next_target = attempt_config['target_candidates'] + TARGET_STEP
        if next_target > attempt_config['max_search_results']:
            if pending:
                raise RuntimeError(f'{pending} repositórios seguem pendentes; teto de busca atingido, '
                                   'inspecione releases_evidence.json/runs_evidence.json.')
            raise RuntimeError(
                f'Só {eligible} elegíveis entre {len(results)} examinados; max_search_results='
                f"{attempt_config['max_search_results']} é o teto configurado para a amostra. "
                'Aumente max_search_results em config.json para ampliar a busca.')
        LOG.info('Só %s elegíveis; ampliando a seleção de %s para %s candidatos com Actions.',
                 eligible, attempt_config['target_candidates'], next_target)
        attempt_config = {**attempt_config, 'target_candidates': next_target}
        attempt += 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'lab03/config.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'lab03/data')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS,
                        help='repositórios processados em paralelo (releases+runs); padrão %(default)s')
    parser.add_argument('--transport', help='modulo:factory; factory() retorna get(path, params)')
    args = parser.parse_args(argv)
    if args.workers <= 0:
        parser.error('--workers deve ser positivo.')
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
    results = run(config, args.out, client, max_workers=args.workers)
    eligible = sum(r['selection_status'] == 'eligible' for r in results)
    print(f'{eligible} repositórios elegíveis de {len(results)} examinados; '
          f'ver {args.out / "final_selection"}.')
    return 0 if eligible >= config['target_candidates'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
