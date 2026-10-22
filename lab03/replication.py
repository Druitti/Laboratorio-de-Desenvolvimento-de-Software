"""Compare a documented 30-repository replication without imputing missing data (#57)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path


CLASSES = {'low': 1, 'medium': 2, 'high': 3, 'elite': 4,
           '1': 1, '2': 2, '3': 3, '4': 4}
TEMPORAL_FIELDS = ('window_start', 'window_end', 'collected_at')
FIELDS = ['repository', 'metric', 'original', 'replicated', 'absolute_difference',
          'relative_difference', 'relative_difference_percent', 'status',
          'original_class', 'replicated_class', 'class_status',
          'window_status', 'collection_status']


def read_table(path, required, repository_column='repository'):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)) or not set(required) <= set(columns):
            raise ValueError(f'Colunas ausentes ou duplicadas: {path}')
        result = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'Linha com quantidade inválida de colunas: {path}')
            repository = row[repository_column].strip()
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
                raise ValueError(f'Identidade inválida: {repository!r}')
            key = repository.casefold()
            if key in result:
                raise ValueError(f'Repositório duplicado: {repository}')
            result[key] = {**row, 'repository': repository}
    return result


def number(value, context):
    if value.strip() == '':
        return None
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError(f'Número inválido: {context}') from error
    if not math.isfinite(result):
        raise ValueError(f'Número não finito: {context}')
    return result


def dora(value, context):
    if not value.strip():
        return None
    key = value.strip().casefold()
    if key in CLASSES:
        return CLASSES[key]
    try:
        numeric = float(key)
    except ValueError:
        numeric = math.nan
    if not math.isfinite(numeric) or numeric not in (1, 2, 3, 4):
        raise ValueError(f'Classe DORA inválida: {context}={value!r}')
    return int(numeric)


def temporal(original, replicated):
    details = {}
    for field in TEMPORAL_FIELDS:
        left, right = original.get(field, '').strip(), replicated.get(field, '').strip()
        details[field] = {'original': left or None, 'replicated': right or None,
                          'status': 'missing' if not left or not right else
                                    'same' if left == right else 'different'}
    window = [details[field]['status'] for field in ('window_start', 'window_end')]
    return details, ('different' if 'different' in window else
                     'missing' if 'missing' in window else 'same')


def compare(original_path, replicated_path, out, metrics, class_column='dora_class',
            selection_path=None, command=None, repository_column='repository'):
    """Align the same explicit 30 identities and preserve every missing pair in audit."""
    out = Path(out)
    if out.exists():
        raise ValueError('Saída já existe; escolha outra pasta.')
    if not metrics or len(metrics) != len(set(metrics)):
        raise ValueError('Informe métricas distintas e explícitas.')
    if any(not metric.strip() or metric in ('repository', repository_column, class_column, *TEMPORAL_FIELDS) for metric in metrics):
        raise ValueError('Nome de métrica inválido ou reservado.')
    if class_column in ('repository', repository_column, *TEMPORAL_FIELDS):
        raise ValueError('Coluna de classificação inválida.')
    paths = {'original': Path(original_path), 'replicated': Path(replicated_path)}
    if selection_path is not None:
        paths['selection'] = Path(selection_path)
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    required = [repository_column, *metrics, class_column]
    original = read_table(original_path, required, repository_column)
    replicated = read_table(replicated_path, required, repository_column)
    selected = read_table(selection_path, ['repository']) if selection_path is not None else replicated
    if len(selected) != 30:
        raise ValueError(f'A comparação exige exatamente 30 repositórios; encontrados {len(selected)}.')
    # Validate every input row, including rows outside the chosen sample.
    numeric, classes = {}, {}
    for source, table in [('original', original), ('replicated', replicated)]:
        for key, row in table.items():
            numeric[source, key] = {metric: number(row[metric], f'{source}/{key}/{metric}') for metric in metrics}
            classes[source, key] = dora(row[class_column], f'{source}/{key}')
    rows, repository_audit = [], []
    same = class_pairs = 0
    for key in sorted(selected):
        left, right = original.get(key, {}), replicated.get(key, {})
        left_class, right_class = classes.get(('original', key)), classes.get(('replicated', key))
        class_status = ('missing_both' if left_class is None and right_class is None else
                        'missing_original' if left_class is None else
                        'missing_replicated' if right_class is None else
                        'same' if left_class == right_class else 'different')
        if left_class is not None and right_class is not None:
            class_pairs += 1
            same += left_class == right_class
        details, window_status = temporal(left, right)
        audit = dict(repository=selected[key]['repository'],
                     original_present=bool(left), replicated_present=bool(right),
                     original_class=left_class, replicated_class=right_class,
                     class_status=class_status, temporal=details)
        repository_audit.append(audit)
        for metric in metrics:
            a = numeric.get(('original', key), {}).get(metric)
            b = numeric.get(('replicated', key), {}).get(metric)
            difference = relative = None
            if a is None or b is None:
                status = ('missing_both' if a is None and b is None else
                          'missing_original' if a is None else 'missing_replicated')
            else:
                difference = abs(b - a)
                relative = (b - a) / abs(a) if a else 0. if b == 0 else None
                status = 'zero_baseline' if a == 0 and b != 0 else 'ok'
                if not math.isfinite(difference) or (relative is not None and not math.isfinite(relative * 100)):
                    raise ValueError(f'Diferença não finita: {key}/{metric}')
            rows.append(dict(repository=selected[key]['repository'], metric=metric, original=a, replicated=b,
                             absolute_difference=difference, relative_difference=relative,
                             relative_difference_percent=None if relative is None else relative * 100,
                             status=status, original_class=left_class, replicated_class=right_class,
                             class_status=class_status, window_status=window_status,
                             collection_status=details['collected_at']['status']))
    summary = dict(repositories=30, metrics=metrics, class_column=class_column, repository_column=repository_column,
                   same_class_repositories=same, class_pairs=class_pairs,
                   class_missing_pairs=30 - class_pairs,
                   same_class_percent=100 * same / class_pairs if class_pairs else None,
                   formula='relative_difference=(replicated-original)/abs(original); percent=100*relative_difference',
                   zero_policy='both zero: 0; original zero and replicated nonzero: null/zero_baseline',
                   missing_policy='blank values or absent repositories remain missing; no imputation',
                   temporal_policy='raw metadata compared as supplied; differences do not establish causes',
                   interpretation='descriptive comparison; different/missing windows prevent asserting equivalent observation periods',
                   input_sha256=hashes, inputs={name: str(path.resolve()) for name, path in paths.items()},
                   command_argv=command or [], command=subprocess.list2cmdline(command or []),
                   excluded_original=sorted(set(original) - set(selected)),
                   excluded_replicated=sorted(set(replicated) - set(selected)),
                   repository_audit=repository_audit,
                   metric_statuses={metric: {status: sum(row['metric'] == metric and row['status'] == status for row in rows)
                                            for status in sorted({row['status'] for row in rows if row['metric'] == metric})}
                                    for metric in metrics})
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != hashes[name] for name, path in paths.items()):
        raise ValueError('Arquivo de entrada mudou durante a comparação.')
    out.mkdir(parents=True)
    with (out/'comparison.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    percent = 'indefinido' if not class_pairs else f'{summary["same_class_percent"]:.2f}%'
    text = ['# Comparação de replicação — 30 repositórios', '',
            f'Mesma classe DORA: {same}/{class_pairs} pares disponíveis ({percent}); {30-class_pairs} pares ausentes.', '',
            'Diferença relativa = (replicado − original) / |original|; porcentagem = 100 × diferença relativa.',
            'Original zero e replicado diferente de zero: resultado relativo indefinido. Ambos zero: 0.',
            'Ausências não são imputadas. Valores originais, replicados e diferenças constam de comparison.csv.', '',
            '## Limites e evidências', '',
            'Metadados temporais ausentes/diferentes são auditados por repositório em summary.json. '
            'Diferenças de coleta ou janela não demonstram a causa de divergências. '
            'Janela diferente ou ausente torna a interpretação condicional; não comprova períodos equivalentes.',
            'Investigar com comandos, logs, versões e fontes antes de atribuir causas ou abrir issues externas.', '',
            '## Comando registrado', '', '```text', summary['command'] or 'API Python; comando não fornecido.', '```', '',
            'Hashes SHA-256 das entradas e repositórios excluídos constam de summary.json.', '']
    (out/'summary.md').write_text('\n'.join(text), encoding='utf-8')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--replicated', type=Path, required=True)
    parser.add_argument('--selection', type=Path, help='CSV com coluna repository e exatamente 30 identidades')
    parser.add_argument('--metrics', nargs='+', required=True, help='Colunas numéricas comuns, na mesma unidade')
    parser.add_argument('--class-column', default='dora_class')
    parser.add_argument('--repository-column', default='repository', help='Coluna de identidade nos dois CSVs; seleção usa repository')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    command = [sys.executable, '-m', 'lab03.replication', *(sys.argv[1:] if argv is None else argv)]
    try:
        compare(args.original, args.replicated, args.out, args.metrics, args.class_column,
                args.selection, command, args.repository_column)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Comparação bloqueada: {error}\n')
    print(f'Comparação exportada: {args.out}')


if __name__ == '__main__':
    main()
