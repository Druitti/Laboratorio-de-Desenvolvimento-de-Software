# RQ03 — Relatório das métricas dos katas

## Como as medições foram feitas

A lista de trials e seus tratamentos vem de `lab02/data/trials.csv`. Para cada uma das 18 linhas, medi o respectivo arquivo final em `lab02/trials/<participante>/<kata>/kata.py`, usando `compute_metrics(caminho, False)` de `lab02/scripts/static_metrics.py` (Radon 6.0.1). A associação de nomes é `Druitti → ferreira`, `gabsant07 → santiago` e `tavares → tavares`. As métricas abaixo foram calculadas diretamente dos arquivos de código, não extraídas do CSV de tempos/testes. Nenhum arquivo do projeto original foi alterado.

**Legenda:** LOC = total de linhas físicas; LLOC = linhas lógicas; SLOC = linhas de código fonte conforme Radon; CC = complexidade ciclomática média por função/bloco; `n` = número de blocos. Em todos os arquivos há uma função medida (`n=1`), então a CC média é igual à CC total.

## Medições individuais

### Druitti

| Kata | Tratamento | LOC | LLOC | SLOC | Comentários | Vazias | CC média | CC total | n |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| k1_merge_intervals | com_ia | 21 | 16 | 13 | 0 | 6 | 5 | 5 | 1 |
| k2_flatten_dict | com_ia | 23 | 14 | 15 | 0 | 6 | 4 | 4 | 1 |
| k3_log_errors | com_ia | 23 | 17 | 14 | 0 | 7 | 4 | 4 | 1 |
| k4_parking_slots | sem_ia | 16 | 13 | 12 | 0 | 3 | 4 | 4 | 1 |
| k5_local_checksum | sem_ia | 15 | 12 | 11 | 0 | 3 | 4 | 4 | 1 |
| k6_frame_score | sem_ia | 18 | 15 | 14 | 0 | 3 | 5 | 5 | 1 |

### gabsant07

| Kata | Tratamento | LOC | LLOC | SLOC | Comentários | Vazias | CC média | CC total | n |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| k1_merge_intervals | sem_ia | 30 | 16 | 13 | 0 | 9 | 4 | 4 | 1 |
| k2_flatten_dict | sem_ia | 32 | 18 | 17 | 0 | 10 | 5 | 5 | 1 |
| k3_log_errors | sem_ia | 30 | 15 | 14 | 0 | 10 | 5 | 5 | 1 |
| k4_parking_slots | com_ia | 23 | 13 | 12 | 0 | 7 | 4 | 4 | 1 |
| k5_local_checksum | com_ia | 32 | 16 | 15 | 0 | 11 | 5 | 5 | 1 |
| k6_frame_score | com_ia | 28 | 12 | 11 | 0 | 9 | 5 | 5 | 1 |

### tavares

| Kata | Tratamento | LOC | LLOC | SLOC | Comentários | Vazias | CC média | CC total | n |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| k1_merge_intervals | com_ia | 18 | 14 | 12 | 1 | 5 | 4 | 4 | 1 |
| k2_flatten_dict | sem_ia | 9 | 9 | 9 | 0 | 0 | 4 | 4 | 1 |
| k3_log_errors | com_ia | 13 | 10 | 9 | 0 | 4 | 3 | 3 | 1 |
| k4_parking_slots | sem_ia | 12 | 12 | 11 | 0 | 0 | 4 | 4 | 1 |
| k5_local_checksum | com_ia | 8 | 7 | 6 | 0 | 2 | 4 | 4 | 1 |
| k6_frame_score | sem_ia | 17 | 16 | 15 | 0 | 1 | 5 | 5 | 1 |

## Comparação dos tratamentos

Mediana / intervalo interquartil (IQR) para os nove trials de cada tratamento. Os quartis usam a mediana das quatro observações abaixo e acima da mediana central.

| Métrica | Com IA (n=9) | Sem IA (n=9) |
|---|---:|---:|
| CC média | 4 / 1 | 4 / 1 |
| LOC | 23 / 10 | 17 / 16.5 |
| SLOC | 12 / 4.5 | 13 / 3.5 |

Para verificar o resultado dentro de cada participante, a tabela seguinte mostra as medianas dos seus três trials por tratamento.

| Participante | CC com IA / sem IA | LOC com IA / sem IA | SLOC com IA / sem IA |
|---|---:|---:|---:|
| Druitti | 4 / 4 | 23 / 16 | 14 / 12 |
| gabsant07 | 5 / 5 | 28 / 30 | 12 / 14 |
| tavares | 4 / 4 | 13 / 12 | 9 / 11 |

## Interpretação da RQ03

A mediana da complexidade ciclomática foi **4 nos dois tratamentos**, e a mediana individual de CC também foi igual com e sem IA para os três participantes. A LOC física foi maior no grupo com IA (23 contra 17), enquanto SLOC ficou próxima (12 contra 13). Logo, nestes trials não há evidência descritiva de mudança na complexidade com o uso de IA; o maior número de linhas físicas, isoladamente, não indica código mais complexo.

A porcentagem de duplicação **não foi medida**: `compute_metrics`/Radon não calcula duplicação. O índice de manutenibilidade (MI) também não foi calculado, porque é opcional e a chamada usou `False`; o retorno `mi: None` em todos os casos é esperado.

**Limitações:** são apenas três participantes e seis katas curtos. Cada participante fez katas distintos em cada tratamento, de modo que as diferenças também podem refletir tarefa e ordem. LOC é relatada como controle descritivo, sem ajuste estatístico. Os resultados dos testes e tempos do `trials.csv` pertencem às outras perguntas de pesquisa; aqui o CSV foi usado para vincular cada solução ao tratamento.

## Arquivos de origem

- Tratamentos: `lab02/data/trials.csv`.
- Códigos medidos: `lab02/trials/ferreira/`, `lab02/trials/santiago/` e `lab02/trials/tavares/`.
- Função de medição: `lab02/scripts/static_metrics.py`, `compute_metrics(path, False)`.
