"""Pré-filtro conservador da integração #44; nunca comprova elegibilidade."""
import copy
import json
import logging

from lab03.releases import pages
from lab03.runs import created_qualifier
from lab03.selection import save_json, timestamp

LOG = logging.getLogger(__name__)


def screen(client, state, out):
    """Descarta apenas quando até o limite superior é menor que o mínimo.

    Releases ainda não têm prova de ancestralidade; total_count de runs inclui
    conclusões ignoradas. Portanto passar aqui exige os dois coletores completos.
    """
    out.mkdir(parents=True, exist_ok=True)
    config = state['config']
    window = {k: config[k] for k in ('window_start', 'window_end')}
    path = out / 'screening.json'
    audit = json.loads(path.read_text()) if path.exists() else {**window, 'repositories': {}}
    if any(audit[k] != window[k] for k in window):
        raise ValueError('Pré-filtro usa outra janela.')
    result, candidates = copy.deepcopy(state), []
    start, end = timestamp(window['window_start']), timestamp(window['window_end'])
    for row in result['repositories']:
        if row['selection_status'] != 'pending_collectors':
            continue
        name = row['repository']
        previous = audit['repositories'].get(name)
        if previous and previous['default_branch'] != row['default_branch']:
            raise ValueError('Branch alterada no pré-filtro; use outra saída.')
        if previous and previous['status'] != 'pending_collectors':
            record = previous
        else:
            record = {'default_branch': row['default_branch'], 'status': 'pending_collectors'}
            try:
                count, ids = 0, set()
                for releases in pages(client, f'/repos/{name}/releases'):
                    for release in releases:
                        if release['id'] in ids:
                            continue
                        ids.add(release['id'])
                        if (not release['draft'] and not release['prerelease']
                                and start <= timestamp(release['published_at']) < end):
                            count += 1
                    if count >= config['min_releases']:
                        break
                record['release_candidates_observed'] = count
                if count < config['min_releases']:
                    record.update(status='excluded_releases', reason='release_upper_bound_below_minimum')
                else:
                    payload, _ = client.get(f'/repos/{name}/actions/runs',
                        {'branch': row['default_branch'], 'event': 'push',
                         'created': created_qualifier(start, end), 'per_page': 1, 'page': 1})
                    record['runs_upper_bound'] = payload['total_count']
                    record['status'] = ('excluded_runs' if payload['total_count'] < config['min_valid_runs']
                                        else 'needs_full_collection')
            except Exception as error:
                record.update(status='pending_collectors', error_type=type(error).__name__)
            audit['repositories'][name] = record
            save_json(path, audit)
        if record['status'] == 'needs_full_collection':
            candidates.append(row)
        else:
            row['selection_status'] = record['status']
        LOG.info('Pré-filtro %s: %s', name, record['status'])
    save_json(out / 'selection_state.json', result)
    return result, candidates
