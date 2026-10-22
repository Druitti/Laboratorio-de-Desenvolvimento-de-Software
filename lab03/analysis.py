"""Análise reproduzível RQ01–07 (#52 #53 #54 #55), sem imputar ausências."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score
from sklearn.metrics import precision_recall_fscore_support
from statsmodels.stats.multitest import multipletests

from lab03.metrics import change_failure_rate, lead_time, recovery_episodes
from lab03.selection import timestamp, read_evidence
from lab03 import validation
from lab03.corrective import classify_repository, calculate_cfr_b, HEURISTIC_VERSION

METRICS = {
    'deployment_frequency': ('Frequência de entrega', 'releases/semana'),
    'lead_time_release_hours': ('Lead time por release', 'horas'),
    'lead_time_commit_hours': ('Lead time por commit', 'horas'),
    'cfr_ci': ('CFR(a): falhas de CI', 'proporção'),
    'cfr_delivery': ('CFR(b): proxy de entrega', 'proporção'),
    'recovery_hours': ('Recuperação de CI', 'horas'),
}
CATEGORIES = {1: 'Low', 2: 'Medium', 3: 'High', 4: 'Elite'}
COMBINATIONS = {
    'C1': ('deployment_frequency', 'lead_time_release_hours', 'cfr_ci'),
    'C2': ('deployment_frequency', 'lead_time_commit_hours', 'cfr_ci'),
    'C3': ('deployment_frequency_pre', 'lead_time_pre_commit_hours', 'cfr_ci'),
    'C4': ('deployment_frequency', 'lead_time_commit_hours', 'cfr_delivery'),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def score(value, metric):
    if value is None or pd.isna(value):
        return None
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'Métrica inválida: {metric}={value}')
    if metric == 'frequency':
        # Um mês = 365/12 dias; conversão explícita para semanas.
        return 4 if value >= 7 else 3 if value >= 1 else 2 if value >= 84 / 365 else 1
    if metric == 'lead':
        return 4 if value < 24 else 3 if value < 168 else 2 if value < 720 else 1
    if metric == 'cfr':
        if value > 1:
            raise ValueError('CFR deve estar entre zero e um.')
        return 4 if value <= .15 else 3 if value <= .30 else 2 if value <= .45 else 1
    if metric == 'recovery':
        return 4 if value < 1 else 3 if value < 24 else 2 if value < 168 else 1
    raise ValueError(metric)


def category(frequency, lead, cfr, recovery):
    scores = [score(x, kind) for x, kind in zip(
        (frequency, lead, cfr, recovery), ('frequency', 'lead', 'cfr', 'recovery'))]
    return math.floor(float(np.median(scores))) if all(x is not None for x in scores) else None


def build_dataset(data, config):
    """Recalcula métricas dos brutos completos e confere o funil e as evidências."""
    data = Path(data)
    eligible = data / 'final_selection/eligible.csv'
    frame = pd.read_csv(eligible, keep_default_na=False)
    if frame.empty or frame.repository.duplicated().any() or frame.repository_id.duplicated().any():
        raise ValueError('Amostra vazia ou com IDs/repositórios duplicados.')
    evidence = [read_evidence(data / filename, config, count) for filename, count in (
        ('releases_evidence.json', 'stable_releases'), ('runs_evidence.json', 'valid_runs'))]
    sources = {str(p): digest(p) for p in (eligible, data / 'releases_evidence.json', data / 'runs_evidence.json')}
    start, end = (timestamp(config[k]) for k in ('window_start', 'window_end'))
    weeks = (end - start).total_seconds() / (7 * 86400)
    if weeks <= 0:
        raise ValueError('Janela inválida.')
    rows = []
    for row in frame.to_dict('records'):
        name, branch = row['repository'], row['default_branch']
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', name) or '..' in name or row['selection_status'] != 'eligible':
            raise ValueError(f'Repositório inválido: {name}')
        raw = []
        for filename in ('releases.json', 'runs.json'):
            path = data / 'raw' / name / filename
            payload = load(path)
            sources[str(path)] = digest(path)
            if (payload.get('complete') is not True or payload['repository'] != name
                    or payload['default_branch'] != branch
                    or any(timestamp(payload[k]) != timestamp(config[k]) for k in ('window_start', 'window_end'))):
                raise ValueError(f'Bruto incompatível/incompleto: {path}')
            raw.append(payload)
        releases, runs = raw
        published = [x['release'] for x in releases['releases'] if x.get('on_default_branch') is True
                     and not x['release']['draft'] and start <= timestamp(x['release']['published_at']) < end]
        stable = [x for x in published if not x['prerelease']]
        valid_runs = runs['runs']
        if (len({x['id'] for x in published}) != len(published)
                or len({x['id'] for x in valid_runs}) != len(valid_runs)
                or any(x['head_branch'] != branch or x['event'] != 'push'
                       or not start <= timestamp(x['created_at']) < end for x in valid_runs)):
            raise ValueError(f'IDs duplicados ou runs fora do escopo: {name}')
        cfr = change_failure_rate(valid_runs)
        recovery = recovery_episodes(valid_runs, config['window_end'])
        nruns = cfr['successes'] + cfr['failures']
        for env, count, value, minimum in zip(evidence, ('stable_releases', 'valid_runs'),
                                             (len(stable), nruns), (5, 50)):
            item = env.get(name)
            if not item or not item['complete'] or item['default_branch'] != branch or item[count] != value or value < minimum:
                raise ValueError(f'Elegibilidade não comprovada: {name}')
        metrics = lead_time(releases['comparisons']['stable'])
        pre = lead_time(releases['comparisons']['with_prereleases'])
        for variant, selected in [('stable', stable), ('with_prereleases', published)]:
            intervals = releases['comparisons'][variant]
            ids = [x['release_id'] for x in intervals]
            if len(set(ids)) != len(ids) or set(ids) != {x['id'] for x in selected}:
                raise ValueError(f'Comparações não cobrem exatamente as releases: {name}/{variant}')
        rows.append({**row, 'stable_releases': len(stable), 'releases_with_pre': len(published),
                     'valid_runs': nruns, 'deployment_frequency': len(stable) / weeks,
                     'deployment_frequency_pre': len(published) / weeks,
                     **{k: metrics[k] for k in ('lead_time_release_hours', 'lead_time_commit_hours', 'ignored_releases')},
                     'lead_time_pre_commit_hours': pre['lead_time_commit_hours'],
                     'cfr_ci': cfr['cfr_ci'], 'cfr_delivery': None,
                     'cfr_delivery_status': 'pending_human_validation',
                     'recovery_hours': recovery['recovery_hours'], 'recovery_episodes': recovery['episodes'],
                     'recovery_censored': recovery['censored'], 'recovery_censored_ratio': recovery['censored_ratio']})
    return pd.DataFrame(rows), sources


def descriptive(frame):
    result = []
    for metric in METRICS:
        values = pd.to_numeric(frame[metric], errors='raise').dropna()
        q = values.quantile([.25, .5, .75])
        result.append({'metric': metric, 'unit': METRICS[metric][1], 'n': len(values),
                       'missing': len(frame) - len(values),
                       'q1': q.iloc[0], 'median': q.iloc[1], 'q3': q.iloc[2], 'iqr': q.iloc[2] - q.iloc[0]})
    return pd.DataFrame(result)


def validated_delivery(frame, data, config, gold):
    """Revalida votos/decisões e fontes antes de avaliar e aplicar a heurística."""
    gold, data = Path(gold), Path(data)
    manifest_path = gold / 'manifest.json'
    manifest = load(manifest_path)
    if (len(manifest['repositories']) != 60 or len(set(manifest['repositories'])) != 60
            or not set(manifest['repositories']) <= set(frame.repository)
            or manifest['population_size'] != len(frame)):
        raise ValueError('Amostra-ouro incompatível com a população analisada.')
    for source, expected in manifest['source_sha256'].items():
        if digest(source) != expected:
            raise ValueError(f'Fonte alterada após sorteio: {source}')
    for dimension, expected in [('project_type', 60), ('real_delivery', 60), ('corrective', 300)]:
        if sum(x['dimension'] == dimension for x in manifest['items']) != expected:
            raise ValueError('Manifesto não contém as três dimensões completas.')
    # Mesma validação da #45: votos individuais completos e divergências confirmadas.
    with tempfile.TemporaryDirectory() as tmp:
        agreed = validation.consensus(manifest_path, gold, gold/'consensus_review.csv', Path(tmp)/'consensus')
        agreement = validation.analyze(manifest_path, gold, Path(tmp)/'agreement')
    predictions, results = {}, {}
    for name in frame.repository:
        raw = load(data/'raw'/name/'releases.json')
        predicted = classify_repository(raw)['predictions']
        results[name] = calculate_cfr_b(predicted, config['window_start'], config['window_end'])
        for row in predicted:
            predictions[(name, str(row['release_id']))] = row['prediction']
    truth, guessed = [], []
    for row in agreed:
        if row['dimension'] == 'corrective':
            truth.append(row['label'])
            guessed.append(predictions[(row['repository'], row['release_id'])])
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, guessed, labels=['yes'], average=None, zero_division=0)
    report = dict(heuristic_version=HEURISTIC_VERSION, n=len(truth), precision=float(precision[0]),
                  recall=float(recall[0]), f1=float(f1[0]), positive_support=int(support[0]),
                  uncertain_predictions=guessed.count('uncertain'), agreement=agreement,
                  interpretation='uncertain is not positive; retains all 300 items in evaluation',
                  validation_kind='same gold sample used for refinement; no held-out estimate')
    frame = frame.copy()
    for field, key in [('cfr_delivery', 'cfr_b'), ('cfr_delivery_denominator', 'denominator'),
                       ('cfr_delivery_censored', 'censored_releases'),
                       ('cfr_delivery_uncertain', 'uncertain_followup_references')]:
        frame[field] = [results[name][key] for name in frame.repository]
    frame['cfr_delivery_status'] = 'validated' if f1[0] >= .7 else 'validation_below_threshold'
    source_hashes = {str(gold/file): digest(gold/file) for file in
                     ['manifest.json', 'consensus_review.csv', *[f'{r}.csv' for r in validation.RATERS]]}
    return frame, report, source_hashes


def correlations(frame):
    rows = []
    for metric in ('cfr_ci', 'cfr_delivery'):
        pairs = frame[['deployment_frequency', metric]].dropna()
        ok = len(pairs) >= 3 and all(pairs[c].nunique() > 1 for c in pairs)
        rho, p = stats.spearmanr(pairs.iloc[:, 0], pairs.iloc[:, 1]) if ok else (None, None)
        rows.append(dict(metric=metric, n=len(pairs), rho=rho, p=p,
                         status='ok' if ok else 'insufficient_or_constant'))
    return pd.DataFrame(rows)


def factor_tests(frame):
    """Três fatores pré-especificados; empates não são quebrados artificialmente."""
    rows, groups_summary = [], []
    for factor in ('stars', 'contributors', 'age_days_at_window_end'):
        values = pd.to_numeric(frame[factor].replace('', np.nan), errors='raise')
        groups = pd.qcut(values, 4, duplicates='drop')
        for metric in METRICS:
            sample = pd.DataFrame({'group': groups, 'value': frame[metric]}).dropna()
            grouped = [(str(key), part.value.to_numpy(dtype=float))
                       for key, part in sample.groupby('group', observed=True, sort=True)]
            for label, v in grouped:
                q = np.quantile(v, [.25, .5, .75])
                groups_summary.append(dict(factor=factor, metric=metric, group=label, n=len(v),
                                           median=q[1], q1=q[0], q3=q[2], iqr=q[2] - q[0]))
            n = len(sample)
            row = dict(factor=factor, metric=metric, n=n, missing=len(frame) - n,
                       groups=len(grouped), test='', statistic=None, p=None, effect=None,
                       effect_type='', status='insufficient_groups')
            if len(grouped) >= 2 and all(len(v) >= 2 for _, v in grouped):
                arrays = [v for _, v in grouped]
                if len(grouped) == 2:
                    stat, p = stats.mannwhitneyu(*arrays, alternative='two-sided', method='auto')
                    effect, kind, test = 2 * stat / (len(arrays[0]) * len(arrays[1])) - 1, 'cliffs_delta', 'Mann-Whitney'
                else:
                    stat, p = (0., 1.) if sample.value.nunique() == 1 else stats.kruskal(*arrays)
                    effect, kind, test = stat / (n - 1), 'epsilon_squared', 'Kruskal-Wallis'
                row.update(test=test, statistic=stat, p=p, effect=effect, effect_type=kind, status='ok')
            rows.append(row)
    result = pd.DataFrame(rows)
    valid = result.p.notna()
    result['p_holm'] = np.nan
    if valid.any():
        result.loc[valid, 'p_holm'] = multipletests(result.loc[valid, 'p'], method='holm')[1]
    result['reject_005'] = result.p_holm < .05
    return result, pd.DataFrame(groups_summary)


def sensitivity(frame):
    classes = frame[['repository']].copy()
    for name, (freq, lead, cfr) in COMBINATIONS.items():
        classes[name] = [category(*row) for row in frame[[freq, lead, cfr, 'recovery_hours']].itertuples(index=False, name=None)]
    rows, matrices = [], []
    for a, b in itertools.combinations(COMBINATIONS, 2):
        pairs = classes[[a, b]].dropna().astype(int)
        n = len(pairs)
        changed = int((pairs[a] != pairs[b]).sum())
        # Kappa indefinido quando os dois vetores só contêm uma mesma categoria.
        defined = n > 0 and len(set(pairs[a]) | set(pairs[b])) > 1
        kappa = float(cohen_kappa_score(pairs[a], pairs[b], labels=[1, 2, 3, 4], weights='linear')) if defined else None
        rows.append(dict(pair=f'{a} x {b}', n=n, excluded=len(frame)-n, changed=changed,
                         changed_percent=100*changed/n if n else None, kappa_linear=kappa,
                         status='ok' if defined else 'undefined_or_missing'))
        for x, y in itertools.product(range(1, 5), repeat=2):
            matrices.append(dict(pair=f'{a} x {b}', source=CATEGORIES[x], target=CATEGORIES[y],
                                 count=int(((pairs[a] == x) & (pairs[b] == y)).sum())))
    return classes, pd.DataFrame(rows), pd.DataFrame(matrices)


def figures(frame, classes, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.2), constrained_layout=True)
    for ax, (metric, (label, unit)) in zip(axes.flat, METRICS.items()):
        v = frame[metric].dropna().sort_values().to_numpy(dtype=float)
        if len(v):
            ax.step(v, np.arange(1, len(v)+1)/len(v), where='post', color='#226790')
            if unit == 'horas' and v.max() > 100:
                ax.set_xscale('symlog', linthresh=1)
                unit += '; symlog (trecho linear até 1 h)'
        else:
            ax.text(.5, .5, 'Pendente de validação humana', ha='center', va='center', transform=ax.transAxes, wrap=True)
        ax.set_title(f'{label}\nn={len(v)}; ausentes={len(frame)-len(v)}', fontsize=10)
        ax.set_xlabel(unit, fontsize=8); ax.set_ylabel('Fração acumulada'); ax.set_ylim(0, 1.02)
        ax.grid(alpha=.15)
    fig.suptitle('Distribuições por repositório — dados disponíveis (2025)', fontsize=13)
    fig.savefig(out/'rq01_04.png', dpi=180); fig.savefig(out/'rq01_04.pdf'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4.3), constrained_layout=True)
    pairs = frame[['deployment_frequency', 'cfr_ci']].dropna()
    ax.scatter(pairs.deployment_frequency, pairs.cfr_ci*100, alpha=.65, s=25, color='#226790')
    ax.set_xscale('log'); ax.set_xlabel('Releases por semana (log)'); ax.set_ylabel('CFR(a): falhas de CI (%)')
    ax.set_title(f'RQ05 — frequência × falhas de CI (n={len(pairs)})'); ax.grid(alpha=.15)
    fig.savefig(out/'rq05.png', dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    counts = classes.C1.value_counts().reindex([1, 2, 3, 4], fill_value=0)
    bars = ax.bar(list(CATEGORIES.values()), counts, color='#226790')
    ax.bar_label(bars); ax.set_ylabel('Repositórios'); ax.set_ylim(0, max(1, counts.max())*1.2)
    ax.set_title(f'C1 — classificação geral; {classes.C1.isna().sum()} sem classificação')
    fig.savefig(out/'classes_c1.png', dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), constrained_layout=True)
    for ax, (a, b) in zip(axes, itertools.combinations(('C1', 'C2', 'C3'), 2)):
        pairs = classes[[a, b]].dropna().astype(int)
        matrix = np.array([[int(((pairs[a] == i) & (pairs[b] == j)).sum())
                            for j in range(1, 5)] for i in range(1, 5)])
        ax.imshow(matrix, cmap='Blues', vmin=0, vmax=max(1, len(pairs)))
        for i, j in itertools.product(range(4), repeat=2):
            ax.text(j, i, str(matrix[i, j]), ha='center', va='center',
                    color='white' if matrix[i, j] > len(pairs)/2 else '#222222')
        ax.set_xticks(range(4), list(CATEGORIES.values()), rotation=35)
        ax.set_yticks(range(4), list(CATEGORIES.values()))
        ax.set_xlabel(b); ax.set_ylabel(a); ax.set_title(f'{a} × {b}; n={len(pairs)}')
    fig.suptitle('RQ07 — contagens de transição; diagonal = mesma classe')
    fig.savefig(out/'rq07.png', dpi=180); plt.close(fig)


def run(data, config, out, exploratory=False, gold=None):
    out = Path(out)
    if out.exists():
        raise ValueError('Saída já existe; escolha outra pasta para preservar a execução anterior.')
    frame, sources = build_dataset(data, config)
    blockers = []
    if len(frame) < 300:
        blockers.append(f'Amostra parcial: {len(frame)}/300 elegíveis (#50).')
    human = None
    if gold:
        frame, human, gold_sources = validated_delivery(frame, data, config, gold)
        sources.update(gold_sources)
        if human['f1'] < .7:
            blockers.append('F1 da heurística abaixo de 0,70: refinamento e reavaliação necessários (#49).')
    else:
        blockers.append('CFR(b) sem validação da heurística contra três avaliações e consenso (#45–49).')
    if blockers and not exploratory:
        raise ValueError('Entrega final bloqueada: ' + ' '.join(blockers) + ' Use --exploratory para diagnóstico identificado.')
    summary = descriptive(frame)
    corr = correlations(frame)
    tests, groups = factor_tests(frame)
    classes, sens, transitions = sensitivity(frame)
    out.mkdir(parents=True)
    for name, table in [('dataset', frame), ('descriptive', summary), ('rq05', corr), ('rq06', tests),
                         ('rq06_groups', groups), ('classes', classes), ('rq07', sens), ('transitions', transitions)]:
        table.to_csv(out/f'{name}.csv', index=False)
    if human:
        save(out/'heuristic_validation.json', human)
    save(out/'manifest.json', dict(status='exploratory_incomplete' if blockers else 'complete', blockers=blockers,
         window_start=config['window_start'], window_end=config['window_end'], repositories=len(frame),
         source_sha256=sources, combinations=COMBINATIONS, holm_family='all valid factor x metric tests',
         quartiles='pandas qcut; tied boundaries collapsed; no arbitrary tie breaking',
         source_code_sha256=digest(__file__)))
    figures(frame, classes, out)
    lines = ['# Resultados e discussão' + (' — execução exploratória' if blockers else ''), '',
             '**Entrega incompleta. Não utilizar como resultado final da Lab03S03.**' if blockers else
             'Execução completa das análises RQ01–07; fontes e configuração no manifesto.', '',
             *[f'- {x}' for x in blockers], '',
             f'Janela: {config["window_start"]} até {config["window_end"]} (fim exclusivo).', '',
             '| Métrica | n | Mediana | Q1–Q3 | Ausentes |', '|---|---:|---:|---:|---:|']
    for r in summary.to_dict('records'):
        fmt = lambda x: '—' if pd.isna(x) else f'{x:.3g}'
        lines.append(f'| {METRICS[r["metric"]][0]} ({r["unit"]}) | {r["n"]} | {fmt(r["median"])} | {fmt(r["q1"])}–{fmt(r["q3"])} | {r["missing"]} |')
    lines += ['', '![Distribuições](rq01_04.png)', '', '## RQ05–06', '']
    for r in corr.to_dict('records'):
        lines.append(f'- {r["metric"]}: n={r["n"]}, rho={fmt(r["rho"])}, p={fmt(r["p"])}; {r["status"]}.')
    lines += ['', f'RQ06: {tests.p.notna().sum()} testes válidos, {(tests.p_holm < .05).sum()} com p ajustado < 0,05. '
              'Resultados por fator, tamanho de efeito e Holm estão em rq06.csv; medianas e IQR por grupo em rq06_groups.csv.',
              '', '![Dispersão](rq05.png)', '', '## RQ07', '',
              'C1 usa release/lead time(a)/CFR(a); C2 altera apenas lead time para (b); '
              'C3 inclui pré-releases e lead time(b), mantendo CFR(a). C4 testa CFR(b), quando validado. '
              'Todas mantêm recuperação de CI. Assim é possível distinguir o efeito de cada definição. '
              'A variante tag não é estimada: a data do commit não comprova a data da tag.', '',
              '| Par | n pareado | Mudaram (%) | Kappa linear |', '|---|---:|---:|---:|']
    for r in sens.to_dict('records'):
        lines.append(f'| {r["pair"]} | {r["n"]} | {fmt(r["changed_percent"])} | {fmt(r["kappa_linear"])} |')
    lines += ['', '![Transições](rq07.png)', '', '![Classes](classes_c1.png)', '', '## Limitações e interpretação', '',
              ('A amostra parcial favorece projetos processados primeiro e não permite generalizar os resultados. ' if blockers else
               'A seleção por popularidade não representa todos os projetos de software. ')+
              'Não concluir causalidade a partir de correlações nem equivalência entre falhas de CI e incidentes em produção. '
              'Medianas de recuperação descrevem apenas episódios encerrados; os censurados são preservados no dataset. '
              'Nenhum episódio observado não equivale a recuperação instantânea. Ausências impedem classificação geral.', '',
              'Estrelas e contribuidores foram medidos na coleta, fora da janela histórica; são covariáveis atuais. '
              'Lead time(a) enfatiza o commit mais antigo de cada release; (b) pondera inclusões individuais de commits. '
              'Diferenças entre as variantes podem refletir commits antigos e tamanhos distintos das releases. '
              'Significância estatística deve ser lida com o tamanho de efeito e a seleção da amostra. '
              'Os testes e pares sem dados permanecem explicitamente ausentes.', '']
    (out/'resultados.md').write_text('\n'.join(lines), encoding='utf-8')
    return frame, blockers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('lab03/data/s02'))
    parser.add_argument('--config', type=Path, default=Path('lab03/config.json'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--exploratory', action='store_true')
    parser.add_argument('--gold', type=Path, help='manifest.json, três CSVs individuais e consensus_review.csv')
    args = parser.parse_args()
    try:
        frame, blockers = run(args.data, load(args.config), args.out, args.exploratory, args.gold)
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2, str(error) + '\n')
    print(f'{len(frame)} repositórios; saída {args.out}; pendências: {" ".join(blockers)}')


if __name__ == '__main__':
    main()
