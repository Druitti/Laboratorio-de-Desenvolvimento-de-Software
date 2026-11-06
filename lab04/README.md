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

## Dashboard (S01: G1 e G2)

Na raiz do repositório, um único comando instala as dependências e abre o dashboard
em `http://localhost:8501`:

```bash
python -m pip install -r lab04/requirements.txt && streamlit run lab04/dashboard.py
```

O dashboard segue as seções do enunciado: 1 Cenário, 2 Os dados (**G1**: histogramas
dos dados reais × simulados), 3 Como os testes funcionam (**G2**: distribuição da
estatística sob H0 para o t de Welch e o U de Mann-Whitney, região de rejeição e
p-valor do exemplo sombreados). As seções 4–7 (G3, G4, tabela dos dados reais e
conclusão) aparecem como pendentes e entram na S02 e na entrega final. Parâmetros
(CSV, observações por grupo, semente, α) ficam na barra lateral; a semente padrão é 42.

- `lab04/null_dist.py`: distribuição nula de cada estatística (t de Welch com gl de
  Welch–Satterthwaite; U por permutação) e p-valor do exemplo.
- `lab04/plots.py`: figuras Plotly de G1 e G2. Cada teste tem uma cor fixa
  (Welch azul, Mann-Whitney laranja), distinta das cores dos grupos em G1.
- `lab04/dashboard.py`: app Streamlit.
- **Dados provisórios:** `lab04/data/real_sample.csv` é um exemplo **sintético** com
  o formato `group,value` (horas) para o dashboard abrir antes da coleta real (#61).
  Substitua o arquivo, ou informe outro caminho na barra lateral, quando os dados
  reais forem integrados; o dashboard avisa enquanto o arquivo provisório estiver em uso.

## Testes

```bash
python -m pytest lab04/tests -q
```

Os testes automatizados estão em `lab04/tests/`.
