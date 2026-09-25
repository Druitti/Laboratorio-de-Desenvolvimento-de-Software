"""Análise reproduzível de RQ1/RQ2; unidade pareada = participante."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median, quantiles

import scipy
from scipy.stats import PermutationMethod, wilcoxon

ROOT = Path(__file__).resolve().parents[2]
KATAS = {p.name for p in (ROOT / 'lab02/katas').glob('k[1-6]_*')}
PARTICIPANTS = {'Druitti', 'gabsant07', 'tavares'}
TREATMENTS = ('com_ia', 'sem_ia')


def read_trials(path):
    with path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    seen = set()
    for row in rows:
        key = (row['integrante'], row['kata'])
        if key in seen:
            raise ValueError(f'Trial duplicado: {key}')
        seen.add(key)
        if key[0] not in PARTICIPANTS or key[1] not in KATAS:
            raise ValueError(f'Participante/kata desconhecido: {key}')
        if row['tratamento'] not in TREATMENTS or row['censurado'] not in ('sim', 'nao'):
            raise ValueError(f'Tratamento/censura inválido: {key}')
        seconds = float(row['tempo_segundos'])
        passed, total, failed = (int(row[k]) for k in
                                ('testes_passando', 'testes_total', 'testes_falhando'))
        if not math.isfinite(seconds) or not 0 <= seconds <= 2100:
            raise ValueError(f'Tempo inválido: {key}')
        if total <= 0 or not 0 <= passed <= total or failed != total - passed:
            raise ValueError(f'Contagem de testes inválida: {key}')
        rate = float(row['taxa_sucesso'])
        if not math.isfinite(rate) or abs(rate - passed / total) > 0.000051:
            raise ValueError(f'Taxa de sucesso inconsistente: {key}')
        if (row['censurado'] == 'sim' and (seconds != 2100 or passed == total)) or (
                row['censurado'] == 'nao' and passed != total):
            raise ValueError(f'Censura inconsistente: {key}')
        row.update(tempo_segundos=seconds, taxa_sucesso=passed / total,
                   testes_falhando=failed)
    if seen != {(p, k) for p in PARTICIPANTS for k in KATAS}:
        raise ValueError('Esperados 18 trials: seis katas por participante.')
    for participant in PARTICIPANTS:
        for treatment in TREATMENTS:
            if sum(r['integrante'] == participant and r['tratamento'] == treatment
                   for r in rows) != 3:
                raise ValueError('Esperados três trials por participante/tratamento.')
    return rows


def paired_test(differences, alternative):
    # O arredondamento evita postos distintos por erro de ponto flutuante.
    differences = [round(d, 10) for d in differences]
    nonzero = [d for d in differences if d != 0]
    if not nonzero:
        return {'status': 'sem_variacao', 'n_pares': len(differences),
                'n_nao_zero': 0, 'estatistica': None, 'p_valor': None,
                'alternativa': alternative, 'metodo': 'não aplicável'}
    # Enumeração exaustiva das trocas de sinal: apenas 2**3 neste desenho.
    result = wilcoxon(differences, alternative=alternative, zero_method='wilcox',
                      method=PermutationMethod(n_resamples=math.inf))
    return {'status': 'ok', 'n_pares': len(differences), 'n_nao_zero': len(nonzero),
            'estatistica': float(result.statistic), 'p_valor': float(result.pvalue),
            'alternativa': alternative, 'metodo': 'permutação exaustiva de sinais'}


def analyze(rows):
    summaries, pairs, tests = [], [], {}
    for metric, alternative in [('tempo_segundos', 'less'), ('taxa_sucesso', 'greater')]:
        differences = []
        for treatment in TREATMENTS:
            values = [r[metric] for r in rows if r['tratamento'] == treatment]
            q1, _, q3 = quantiles(values, n=4, method='inclusive')
            summaries.append({'metrica': metric, 'tratamento': treatment,
                              'n_trials': len(values), 'mediana': median(values),
                              'q1': q1, 'q3': q3, 'iqr': q3 - q1})
        for participant in sorted(PARTICIPANTS):
            values = {t: median(r[metric] for r in rows
                               if r['integrante'] == participant and r['tratamento'] == t)
                      for t in TREATMENTS}
            difference = round(values['com_ia'] - values['sem_ia'], 10)
            pairs.append({'integrante': participant, 'metrica': metric, **values,
                          'diferenca_com_menos_sem': difference})
            differences.append(difference)
        tests[metric] = paired_test(differences, alternative)
    return summaries, pairs, tests


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'lab02/data/trials.csv')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'lab02/data/analise_rq1_rq2')
    args = parser.parse_args()
    rows = read_trials(args.input)
    summaries, pairs, tests = analyze(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / 'resumo.csv', summaries)
    write_csv(args.output_dir / 'pares.csv', pairs)
    result = {'fonte_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'scipy': scipy.__version__, 'alpha': 0.05,
              'unidade_pareada': 'mediana por participante e tratamento',
              'n_trials': len(rows), 'n_censurados': sum(r['censurado'] == 'sim' for r in rows),
              'rq1_estimando': 'tempo observado limitado a 2100 s; não estima tempo após censura',
              'testes': tests}
    (args.output_dir / 'resultados.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
