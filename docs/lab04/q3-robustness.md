# Lab04S02 — Q3: assimetria e outliers

10,000 repetições por efeito, n=30 por grupo, α=5%, semente 42. Os efeitos são deslocamentos em log(horas); a razão de medianas do segundo grupo é exp(efeito).

O cenário de referência usa uma lognormal ajustada à amostra real. O cenário não ideal multiplica por 20 cada observação com probabilidade 5%, igualmente nos dois grupos sob H0.

## Q1 — erro tipo I sob H0

| Condição | Welch | Mann–Whitney | Referência α |
|---|---:|---:|---:|
| Lognormal de referência | 1.5% | 4.7% | 5% |
| Com outliers | 1.1% | 4.4% | 5% |

## Q2/Q3 — poder por tamanho do efeito

| Efeito log | Razão das medianas | Welch referência | MW referência | Welch outliers | MW outliers |
|---:|---:|---:|---:|---:|---:|
| 0.00 | 1.00× | 1.5% | 4.7% | 1.1% | 4.4% |
| 0.20 | 1.22× | 1.7% | 5.9% | 1.4% | 6.0% |
| 0.40 | 1.49× | 2.0% | 8.7% | 1.8% | 8.2% |
| 0.60 | 1.82× | 3.4% | 15.2% | 2.8% | 14.7% |
| 0.80 | 2.23× | 4.3% | 22.0% | 3.4% | 21.1% |
| 1.00 | 2.72× | 6.1% | 32.4% | 4.6% | 31.1% |

## Interpretação

welch: erro tipo I 1.5% no modelo de referência e 1.1% com outliers (variação -0.4 pontos percentuais; alfa=5%). mann_whitney: erro tipo I 4.7% no modelo de referência e 4.4% com outliers (variação -0.3 pontos percentuais; alfa=5%). No maior efeito simulado, poder na referência e com outliers: Welch 6.1% e 4.6%; Mann–Whitney 32.4% e 31.1%.

A condição de referência também é assimétrica; Q3 mede o acréscimo de uma cauda ainda mais pesada pela contaminação especificada. Compare erro tipo I com α antes de comparar poder. As conclusões valem para este modelo e estes tamanhos amostrais, não para todos os dados de tempo de PR.

## Limitações

- O modelo de contaminação é uma condição simulada, não uma afirmação sobre a frequência real de outliers.
- Welch e Mann–Whitney são avaliados sob o mesmo modelo e a mesma amostra de entrada.
- Mann–Whitney usa aproximação normal assintótica; a interpretação de localização requer formas semelhantes.
- As simulações estimam erro tipo I e poder do modelo, não causalidade do uso de bots.
