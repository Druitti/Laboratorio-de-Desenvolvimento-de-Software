# Lab04S01 — simulação e comparação de testes

Este módulo cobre o cenário P1 do enunciado: comparar o tempo até o merge de
pull requests com e sem bot de revisão. É um cenário de dois grupos independentes.
O par implementado é **t de Welch × Mann–Whitney**, ambos bilaterais: Welch
compara médias sem supor variâncias iguais; Mann–Whitney é um teste por postos que
compara as distribuições (uma interpretação como diferença de localização requer
formatos semelhantes). O grupo deve confirmar essa
escolha ao consolidar o cenário em #61.

## Dados de entrada

O CSV fornecido pela issue #61 deve conter `group,value`, com dois grupos e
`value` sendo o tempo até o merge, positivo e medido em horas. Não há dados reais
embutidos neste módulo. A amostra de teste automatizado é sintética e não deve ser
interpretada como coleta real.

## Executar

Na raiz do repositório, instale a dependência adicional e execute:

```bash
python -m pip install -r lab04/requirements.txt
python -m lab04.simulation --input caminho/para/dados_reais.csv --seed 42
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

- H0: os tempos dos grupos são iguais.
- H1: os tempos dos grupos diferem.
- Unidade: horas até o merge de cada pull request.
- Limite: a lognormal é uma aproximação ajustada à amostra real; a amostra pequena
  pode representar mal a cauda. A S02 avaliará comportamento sob violações dos
  pressupostos.

Os testes automatizados estão em `lab04/tests/`.
