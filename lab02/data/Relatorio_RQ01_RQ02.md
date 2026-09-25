# Lab02S03 — RQ1/RQ2: tempo e defeitos

Responsável: Gabriel Ferreira Amaral (`Druitti`). Issue #35, parte de #16.

## Fonte e reprodução

A análise usa exclusivamente os 18 registros existentes em `lab02/data/trials.csv`,
sem alterar ou reconstruir medições. São três participantes, seis katas por pessoa,
três trials por tratamento e nenhum registro censurado. O desenho e as hipóteses
vêm de `docs/lab02/desenho-experimento.md`; a divisão vem de
`docs/lab02/divisao-lab02.md` e da issue #16. O enunciado original não está
presente neste checkout; a aderência a requisitos adicionais depende desse documento.

Na raiz do repositório (ambiente validado: Python 3.12):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r lab02/requirements-analysis.txt
python lab02/scripts/analyze_rq1_rq2.py
python -m pytest lab02/scripts lab02/katas/reference -q
```

Saídas em `lab02/data/analise_rq1_rq2/`: `resumo.csv` (mediana e quartis por
tratamento), `pares.csv` (medianas individuais e diferenças) e `resultados.json`
(teste, versão do SciPy, contagem de censura e SHA-256 do CSV de origem).
`--input` e `--output-dir` permitem mudar os caminhos. A validação rejeita
trials duplicados/ausentes, valores não finitos, contagens inconsistentes e
tratamentos sem três medições por pessoa. A taxa é recalculada a partir das contagens.

## Método e hipóteses

A unidade pareada é **o participante**: calculamos a mediana dos três trials
com IA e dos três sem IA de cada pessoa. Assim há **três pares**, não nove.
Nenhuma pessoa repetiu o mesmo kata nos dois tratamentos; parear linhas pela
posição do CSV criaria uma correspondência artificial. Agregar por pessoa
preserva o desenho within-subject, embora não elimine diferenças de dificuldade
entre conjuntos de katas.

- **RQ1:** H0: diferenças de tempo centradas em zero; H1: tempo com IA menor
  (`com_ia − sem_ia < 0`, teste unilateral `less`).
- **RQ2:** H0: diferenças da taxa de sucesso centradas em zero; H1: taxa com IA
  maior (`com_ia − sem_ia > 0`, teste unilateral `greater`). A taxa é a métrica
  primária prevista; falhas absolutas são complementares, pois K1 tem seis testes
  e os demais têm cinco.

Usamos Wilcoxon signed-rank com alfa de 0,05, postos das diferenças arredondadas
para evitar ruído numérico e permutação exaustiva de sinais (`PermutationMethod`),
que também permite empates. A estatística unilateral é a soma dos postos positivos.
Diferenças zero são removidas dos postos (`zero_method='wilcox'`); se todas são
zero, o script retorna `sem_variacao` com estatística e p-valor nulos, sem simular
um teste informativo. O teste pressupõe diferenças independentes entre pessoas e
uma distribuição simétrica sob H0; três pessoas não permitem avaliar a simetria.
Referência técnica: [documentação oficial do SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html).

Os quartis descritivos usam interpolação linear inclusiva (`statistics.quantiles`,
`method='inclusive'`, equivalente ao tipo 7), e IQR = Q3 − Q1. O relatório RQ3
existente usa outra convenção de quartis; seus IQRs não devem ser comparados sem
padronizar o método. Não aplicamos ajuste por múltiplas comparações: RQ2 é
não informativa e RQ1 já não rejeita H0 mesmo sem ajuste.

## Resultados descritivos

| Métrica | Com IA (9 trials) | Sem IA (9 trials) |
|---|---:|---:|
| Tempo mediano (s) | 8,83 | 245,54 |
| Q1 / Q3 do tempo (s) | 6,21 / 17,32 | 22,08 / 459,21 |
| IQR do tempo (s) | 11,11 | 437,13 |
| Taxa de sucesso mediana | 100% | 100% |
| IQR da taxa de sucesso | 0 | 0 |
| Testes falhando ao final (soma) | 0 | 0 |

As nove observações por grupo são apenas uma descrição dos trials, não nove
unidades independentes para a inferência pareada.

| Participante | Mediana com IA (s) | Mediana sem IA (s) | Diferença (s) |
|---|---:|---:|---:|
| Druitti | 8,70 | 21,94 | −13,24 |
| gabsant07 | 16,22 | 245,54 | −229,32 |
| tavares | 17,32 | 664,54 | −647,22 |

## RQ1 — Inferência e interpretação

**W+ = 0; p unilateral = 0,125; n = 3 pares.** Não rejeitamos H0 a 5%.
Todos os participantes apresentam menor mediana de tempo registrada com IA;
a mediana das diferenças individuais é **−229,32 s**. Essa descrição não
estabelece que a IA cause a redução nem oferece evidência estatística suficiente
para confirmar H1 nesta amostra.

Com três diferenças não nulas, há apenas oito configurações de sinais. Mesmo
com todas favoráveis à hipótese, o menor p unilateral possível é 1/8 = 0,125.
Portanto, este desenho não consegue alcançar alfa de 5% com o teste exato
escolhido. A ausência de significância não demonstra igualdade entre tratamentos.

## RQ2 — Inferência e interpretação

Todos os 18 trials terminaram com 100% dos testes passando. As medianas
individuais são 1 nos dois tratamentos, produzindo diferenças **[0, 0, 0]**.
Não há pares com diferença não nula para Wilcoxon: **estatística e p-valor não
aplicáveis**. Não é possível concluir redução de defeitos ou equivalência.

O cronômetro encerra no green, portanto a taxa final apresenta efeito teto
quando ninguém atinge o limite de tempo. Zero testes falhando não significa
código sem defeitos; significa apenas sucesso nos testes de aceitação existentes.
Uma coleta futura poderia registrar falhas na primeira submissão e tentativas
até green, com protocolo definido antes dos trials.

## Censura e ameaças à validade

Nenhum trial atual foi censurado. Se ocorrer censura, o script mantém o registro
em 2100 s, analisando o tempo observado limitado ao time-box, conforme o desenho.
Isso não estima o tempo real até green além de 35 minutos; uma análise de
sobrevivência seria necessária para essa pergunta. A taxa final continua sendo
calculada, inclusive para trials censurados.

Os tempos de alguns trials são de poucos segundos, inclusive de Druitti sem IA.
O CSV isolado não comprova se a cronometragem começou antes da implementação,
se houve preparação prévia ou se as condições de uso de IA foram respeitadas.
É necessário conferir a procedência com os registros de execução antes de tratar
os valores como duração integral de programação. Não excluímos nem corrigimos
esses registros sem evidência.

Outras limitações: três estudantes, tarefas curtas, diferenças de dificuldade,
ordem/aprendizado, familiaridade individual e cobertura restrita dos testes.
Resultados são exploratórios e restritos aos dados registrados. RQ3 e o dashboard
continuam nas responsabilidades de Santiago e Tavares; esta entrega cobre a
parte de Ferreira na Sprint 3.
