"""Amostra-ouro e concordância de Ferreira (#45); não produz rótulos humanos."""
import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

from lab03.selection import read_evidence, timestamp, write_csv

RATERS = ('Druitti', 'gabsant07', 'Tavaresds1')
CATEGORIES = {
    'project_type': ('library_framework', 'application_service', 'cli', 'other'),
    'real_delivery': ('yes', 'no', 'uncertain'),
    'corrective': ('yes', 'no'),
}
LABEL_FIELDS = ['item_id', 'repository', 'dimension', 'release_id', 'url', 'label', 'notes']


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def fresh(path):
    """Nunca sobrescrever formulário preenchido ou resultados de outra execução."""
    path = Path(path)
    if path.exists():
        raise ValueError(f'Saída já existe: {path}; escolha nova pasta.')
    return path


def prepare(eligible, data, config, out, seed=42):
    """Congela 60 repositórios/300 releases reais a partir da entrega de #50."""
    out, data = fresh(out), Path(data)
    rows = read_csv(eligible)
    if len(rows) < 300:
        raise ValueError('Amostra final precisa de pelo menos 300 repositórios elegíveis (#50).')
    names = [r['repository'] for r in rows]
    if len(set(names)) != len(names) or any(not re.fullmatch(r'[\w.-]+/[\w.-]+', n) or '..' in n for n in names):
        raise ValueError('Repositórios duplicados ou nomes inválidos.')
    start, end = timestamp(config['window_start']), timestamp(config['window_end'])
    if start >= end:
        raise ValueError('Janela inválida.')
    releases_path, runs_path = data / 'releases_evidence.json', data / 'runs_evidence.json'
    releases = read_evidence(releases_path, config, 'stable_releases')
    runs = read_evidence(runs_path, config, 'valid_runs')
    for row in rows:
        a, b = releases.get(row['repository']), runs.get(row['repository'])
        if (row['selection_status'] != 'eligible' or not a or not b
                or not a['complete'] or not b['complete']
                or a['stable_releases'] < 5 or b['valid_runs'] < 50
                or any(x['default_branch'] != row['default_branch'] for x in (a, b))):
            raise ValueError(f"Elegibilidade incompleta/inconsistente: {row['repository']}")
    rng = random.Random(seed)
    selected = sorted(rng.sample(sorted(names), 60))
    sources = {str(p): digest(p) for p in (Path(eligible), releases_path, runs_path)}
    items = []
    for name in selected:
        path = data / 'raw' / name / 'releases.json'
        raw = read_json(path)
        sources[str(path)] = digest(path)
        if (raw.get('complete') is not True or raw['repository'] != name
                or raw['default_branch'] != releases[name]['default_branch']
                or any(timestamp(raw[k]) != timestamp(config[k]) for k in ('window_start', 'window_end'))):
            raise ValueError(f'Raw de releases incompatível: {name}')
        stable = [x['release'] for x in raw['releases']
                  if x.get('on_default_branch') is True and x['status'] == 'in_window'
                  and x['release']['draft'] is False and x['release']['prerelease'] is False
                  and start <= timestamp(x['release']['published_at']) < end]
        if (len(stable) < 5 or len(stable) != releases[name]['stable_releases']
                or len({r['id'] for r in stable}) != len(stable)):
            raise ValueError(f'Releases insuficientes, duplicadas ou contagem divergente: {name}')
        for dimension in ('project_type', 'real_delivery'):
            items.append(dict(item_id=f'{name}:{dimension}', repository=name, dimension=dimension,
                              release_id='', url=f'https://github.com/{name}'))
        for release in sorted(rng.sample(sorted(stable, key=lambda r: r['id']), 5), key=lambda r: r['id']):
            url = release['html_url']
            if not url.startswith(f'https://github.com/{name}/releases/'):
                raise ValueError('Link de release inválido.')
            items.append(dict(item_id=f"{name}:corrective:{release['id']}", repository=name,
                              dimension='corrective', release_id=str(release['id']), url=url))
    manifest = dict(schema_version=1, seed=seed, sampling='sorted population; Python random.Random.sample',
                    population_size=len(rows), window_start=config['window_start'], window_end=config['window_end'],
                    repositories=selected, items=items, source_sha256=sources, raters=list(RATERS))
    out.mkdir(parents=True)
    save(out / 'manifest.json', manifest)
    for rater in RATERS:
        write_csv(out / f'{rater}.csv', [{**i, 'label': '', 'notes': ''} for i in items], LABEL_FIELDS)
    return manifest


def load_labels(manifest, folder):
    expected = {i['item_id']: i for i in manifest['items']}
    if len(expected) != len(manifest['items']) or not expected:
        raise ValueError('Manifesto vazio ou com itens duplicados.')
    result = {}
    for rater in RATERS:
        rows = read_csv(Path(folder) / f'{rater}.csv')
        indexed = {r['item_id']: r for r in rows}
        if len(indexed) != len(rows) or set(indexed) != set(expected):
            raise ValueError(f'Itens ausentes, extras ou duplicados: {rater}')
        for key, item in expected.items():
            row = indexed[key]
            if any(row[k] != str(item[k]) for k in ('repository', 'dimension', 'release_id', 'url')):
                raise ValueError(f'Identificação alterada: {rater}/{key}')
            if row['label'] not in CATEGORIES[item['dimension']]:
                raise ValueError(f'Rótulo ausente/inválido: {rater}/{key}')
        result[rater] = indexed
    return result


def agreement(labels, categories):
    """Fleiss nominal; caso de uma única categoria global é indefinido, não 1."""
    from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa
    if not labels or any(len(row) != 3 for row in labels):
        raise ValueError('São necessários itens e exatamente três avaliadores.')
    encoded = [[categories.index(value) for value in row] for row in labels]
    counts, _ = aggregate_raters(encoded, n_cat=len(categories))
    totals = counts.sum(axis=0)
    if sum(totals > 0) == 1:
        return dict(n=len(labels), kappa=None, status='undefined_single_category')
    return dict(n=len(labels), kappa=float(fleiss_kappa(counts, method='fleiss')), status='measured')


def analyze(manifest_path, labels_dir, out):
    out = fresh(out)
    manifest = read_json(manifest_path)
    labels = load_labels(manifest, labels_dir)
    report, proposals = {}, []
    for dimension, categories in CATEGORIES.items():
        values = [[labels[r][i['item_id']]['label'] for r in RATERS]
                  for i in manifest['items'] if i['dimension'] == dimension]
        report[dimension] = agreement(values, categories)
    for item in manifest['items']:
        votes = [labels[r][item['item_id']]['label'] for r in RATERS]
        top, count = Counter(votes).most_common(1)[0]
        proposals.append(dict(item_id=item['item_id'], dimension=item['dimension'],
                              **dict(zip(RATERS, votes)), suggested_label=top if count >= 2 else '',
                              status='unanimous' if count == 3 else 'discussion_required',
                              label='', rationale='', confirmed_by=''))
    report['provenance'] = dict(manifest_sha256=digest(manifest_path),
                               labels_sha256={r: digest(Path(labels_dir) / f'{r}.csv') for r in RATERS})
    out.mkdir(parents=True)
    save(out / 'agreement.json', report)
    write_csv(out / 'consensus_review.csv', proposals, list(proposals[0]))
    return report


def consensus(manifest_path, labels_dir, decisions_path, out):
    """Só exporta desacordos após decisão documentada dos três; nunca altera rótulos."""
    out = fresh(out)
    manifest = read_json(manifest_path)
    labels = load_labels(manifest, labels_dir)
    rows = read_csv(decisions_path)
    decisions = {r['item_id']: r for r in rows}
    if len(decisions) != len(rows) or set(decisions) != {i['item_id'] for i in manifest['items']}:
        raise ValueError('Decisões devem cobrir exatamente os itens do manifesto.')
    result = []
    for item in manifest['items']:
        votes = [labels[r][item['item_id']]['label'] for r in RATERS]
        decision = decisions[item['item_id']]
        if any(decision.get(r) != vote for r, vote in zip(RATERS, votes)):
            raise ValueError('Votos mudaram desde a análise; gere nova revisão de consenso.')
        if len(set(votes)) == 1:
            value, rationale = votes[0], 'unanimous'
            if decision.get('label') not in ('', value):
                raise ValueError('Decisão contradiz unanimidade; revise o protocolo.')
        else:
            value, rationale = decision['label'], decision['rationale'].strip()
            if (value not in CATEGORIES[item['dimension']] or not rationale
                    or set(decision['confirmed_by'].split(';')) != set(RATERS)):
                raise ValueError(f"Desacordo sem decisão confirmada: {item['item_id']}")
        result.append({**item, 'label': value, 'rationale': rationale})
    out.mkdir(parents=True)
    write_csv(out / 'consensus.csv', result, list(result[0]))
    save(out / 'provenance.json', dict(manifest_sha256=digest(manifest_path),
         decisions_sha256=digest(decisions_path),
         labels_sha256={r: digest(Path(labels_dir) / f'{r}.csv') for r in RATERS}))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--eligible', type=Path, required=True)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--config', type=Path, default=Path('lab03/config.json'))
    p.add_argument('--seed', type=int, default=42)
    for name in ('analyze', 'consensus'):
        p = sub.add_parser(name)
        p.add_argument('--manifest', type=Path, required=True)
        p.add_argument('--labels', type=Path, required=True)
        if name == 'consensus':
            p.add_argument('--decisions', type=Path, required=True)
    for p in sub.choices.values():
        p.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    try:
        if a.command == 'prepare':
            prepare(a.eligible, a.data, read_json(a.config), a.out, a.seed)
        elif a.command == 'analyze':
            analyze(a.manifest, a.labels, a.out)
        else:
            consensus(a.manifest, a.labels, a.decisions, a.out)
    except (ValueError, KeyError, FileNotFoundError) as error:
        parser.exit(2, f'Entrada incompleta ou inválida: {error}\n')


if __name__ == '__main__':
    main()
