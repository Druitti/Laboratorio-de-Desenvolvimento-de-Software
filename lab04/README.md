# Lab04S01 — simulação e comparação de testes

Este módulo cobre o cenário P1 do enunciado: comparar o tempo até o merge de
pull requests com e sem bot de revisão. É um cenário de dois grupos independentes.
O par implementado é **t de Welch × Mann–Whitney**, ambos bilaterais: Welch
compara médias sem supor variâncias iguais; Mann–Whitney é um teste por postos que
compara as distribuições (uma interpretação como diferença de localização requer
formatos semelhantes). O cenário, as hipóteses e a justificativa do par com base
nos dados reais estão em [cenário e dados](../docs/lab04/cenario-dados.md) (#61).

## Dados de entrada

A amostra real da issue #61 está em `lab04/data/real_prs.csv`: 30 PRs por grupo,
com fonte, método e limitações em cada linha. A simulação usa as colunas
`group,value`, com `value` sendo o tempo até o merge, positivo e medido em horas.
A amostra de `lab04/tests/test_simulation.py` é sintética e não deve ser
interpretada como coleta real.

Para ler e validar a amostra real, e regenerar `lab04/data/real_summary.json`:

```bash
python -m lab04.real_data
```

## Executar

Na raiz do repositório, instale as dependências adicionais e execute:

```bash
python -m pip install -r lab04/requirements.txt
python -m lab04.simulation --input lab04/data/real_prs.csv --seed 42
```

Por padrão, são geradas 30 observações simuladas por grupo. Os parâmetros da
lognormal são estimados separadamente a partir da média e do desvio-padrão amostral
dos logaritmos dos tempos reais de cada grupo. A mesma semente e os mesmos dados
produzem a mesma simulação. O comando grava `lab04/data/simulated.csv` e
`lab04/data/comparison.json`; ambos podem ser alterados com `--output` e `--summary`.
Use `--n-per-group` e `--alpha` para configurar tamanho e nível de significância.

O JSON inclui estatísticas, p-valores, descrições, hipótese nula e alternativa
específicas de cada teste e interpretação a 5% (ou ao alpha escolhido). Não rejeitar
H0 não demonstra que os grupos são iguais. Um resultado de
uma simulação é ilustrativo; erro tipo I e poder serão estimados por repetição em
Q1/Q2 na S02.

## Hipóteses do cenário

- H0 e H1 de cada teste: ver [cenário e dados](../docs/lab04/cenario-dados.md).
- Unidade: horas até o merge de cada pull request.
- Limite: a lognormal é uma aproximação ajustada à amostra real; a amostra pequena
  pode representar mal a cauda. A S02 avaliará comportamento sob violações dos
  pressupostos.

## Execução integrada

Na raiz do repositório, instale as dependências uma vez e execute o pipeline integrado:

```bash
python -m pip install -r lab04/requirements.txt
python -m lab04 --seed 42 --n-per-group 30 --repetitions 10000
```

O comando valida a amostra real, gera uma amostra ilustrativa e resultados Q3
reproduzíveis e então abre o dashboard em `http://localhost:8501`. O CSV da coleta
está versionado; a reprodução não consulta a API do GitHub. Para refazer a coleta
de rede, consulte [cenário, fonte e método](../docs/lab04/cenario-dados.md).

O dashboard segue as seções do enunciado: 1 Cenário, 2 Os dados (**G1**), 3 Como os
testes funcionam (**G2**), 4 Erro tipo I, 5 Poder, 6 Dados reais e 7 Conclusão.
As seções 4 e 5 trazem o **G3** (erro tipo I de Welch e Mann–Whitney em cada situação, com
linha em α e IC de 95% da simulação) e o **G4** (curvas de poder dos dois testes no mesmo
gráfico, cor = teste e tracejado = outliers), cada um com texto gerado a partir de
`lab04/data/q3_robustness.json`; as tabelas de Q1/Q2 ficam em expansores. A seção 4 também
mostra o erro tipo I por tamanho amostral, e a seção 5 traz um complemento do G4 com o poder
por tamanho amostral e por assimetria, a partir de `lab04/data/q1_q2.json` (#64). A seção 6
aplica os dois testes aos dados reais, com estatística, p-valor, tamanho do efeito e conclusão,
e a seção 7 compara a expectativa registrada antes das simulações com os resultados (#67).
CSV, tamanho amostral, semente e
alfa podem ser alterados na interface; a linha de comando aceita os mesmos parâmetros
de simulação.

- `lab04/null_dist.py`: distribuição nula de cada estatística (t de Welch com gl de
  Welch–Satterthwaite; U por permutação) e p-valor do exemplo.
- `lab04/plots.py`: figuras Plotly de G1 a G4. Cada teste tem uma cor fixa
  (Welch azul, Mann-Whitney laranja), distinta das cores dos grupos em G1.
- `lab04/dashboard.py`: app Streamlit; exibe os links locais e do repositório/quadro no topo.
- `lab04/power.py`: Q1/Q2 (#64), erro tipo I e poder por efeito, tamanho amostral e assimetria;
  grava `lab04/data/q1_q2.json` e [`docs/lab04/q1-q2.md`](../docs/lab04/q1-q2.md).
- `lab04/robustness.py`: Q3, repetindo Q1/Q2 com uma contaminação por outliers.
- `lab04/__main__.py`: validação, geração dos artefatos e abertura do dashboard num comando.
- **Dados reais:** o dashboard abre com a amostra da #61, `lab04/data/real_prs.csv`.
  Outro CSV com `group,value` (horas) pode ser informado na barra lateral.

## Testes

```bash
python -m pytest lab04/tests -q
```

Os testes automatizados estão em `lab04/tests/`.

## Apresentação oral

As respostas preparadas por Santiago para as perguntas 4, 8, 10 e 15 estão em
[`docs/lab04/apresentacao-santiago.md`](../docs/lab04/apresentacao-santiago.md).
Incluem parâmetros estimados dos dados reais, resultados de Q3 e as limitações
necessárias para explicar a recomendação.
