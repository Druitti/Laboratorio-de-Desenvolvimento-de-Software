# Resumo estatístico — Lab02 (com_ia vs sem_ia)

- Trials (RQ1/RQ2): 18
- Trials com métricas estáticas (RQ3): 18

Mediana e IQR (Q3 - Q1) por tratamento. Métricas escolhidas por RQ em `docs/lab02/desenho-experimento.md`.

## tempo_segundos — RQ1 (s)

| tratamento | n | média | mediana | q1 | q3 | iqr |
|---|---|---|---|---|---|---|
| Sem IA | 9 | 473.86 | 459.21 | 426.47 | 521.25 | 94.78 |
| Com IA | 9 | 12.54 | 8.83 | 6.21 | 17.32 | 11.11 |

> Note a média acima da mediana nos dois tratamentos (mais pronunciado no `com_ia`) — sinal de assimetria à direita, típica de métricas de tempo em Engenharia de Software (um ou dois trials mais lentos puxam a média para cima). É por isso que a RQ1 usa mediana + IQR como métrica primária, não a média (ver `docs/lab02/desenho-experimento.md`).

## taxa_sucesso — RQ2

| tratamento | n | média | mediana | q1 | q3 | iqr |
|---|---|---|---|---|---|---|
| Sem IA | 9 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| Com IA | 9 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |

## testes_falhando — RQ2

| tratamento | n | média | mediana | q1 | q3 | iqr |
|---|---|---|---|---|---|---|
| Sem IA | 9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Com IA | 9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## complexidade_media — RQ3

| tratamento | n | média | mediana | q1 | q3 | iqr |
|---|---|---|---|---|---|---|
| Sem IA | 9 | 4.44 | 4.00 | 4.00 | 5.00 | 1.00 |
| Com IA | 9 | 4.22 | 4.00 | 4.00 | 5.00 | 1.00 |

## loc — RQ3 (controle)

| tratamento | n | média | mediana | q1 | q3 | iqr |
|---|---|---|---|---|---|---|
| Sem IA | 9 | 19.89 | 17.00 | 15.00 | 30.00 | 15.00 |
| Com IA | 9 | 21.00 | 23.00 | 18.00 | 23.00 | 5.00 |

## mi — RQ3

| tratamento | n | média | mediana | q1 | q3 | iqr |
|---|---|---|---|---|---|---|
| Sem IA | 9 | 75.78 | 65.90 | 63.09 | 90.03 | 26.94 |
| Com IA | 9 | 79.46 | 81.11 | 68.13 | 89.91 | 21.78 |

**Nota (RQ2):** todos os trials coletados atingiram 100% dos testes de aceitação (`taxa_sucesso = 1.0`, `testes_falhando = 0`) — não houve variância de defeitos nesta amostra (efeito teto). A RQ2 fica limitada a essa constatação; uma amostra maior ou katas mais difíceis seriam necessários para observar diferença de defeitos entre tratamentos.