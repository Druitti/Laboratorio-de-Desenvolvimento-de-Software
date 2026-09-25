# Lab02 — Dashboard (Issue #16)

Issue: **#16** (S03 — Análise + dashboard) · Responsável: Gabriel Tavares (`Tavaresds1`)

Gráficos e resumo estatístico comparando `com_ia` vs `sem_ia`, gerados a partir de
`lab02/data/trials.csv` (RQ1/RQ2) e `lab02/data/static_metrics.csv` (RQ3) pelo
script `lab02/scripts/dashboard.py`.

## Como reproduzir

Na raiz do projeto:

```bash
python -m pip install -r requirements.txt
python lab02/scripts/dashboard.py
```

Isso lê os CSVs padrão em `lab02/data/` e regrava todos os arquivos desta pasta.
Para usar outros arquivos/pasta de saída:

```bash
python lab02/scripts/dashboard.py --trials-csv <csv> --metricas-csv <csv> --out-dir <pasta>
```

Testes do script:

```bash
python -m pytest lab02/scripts/test_dashboard.py -q
```

## Artefatos gerados

| Arquivo | RQ | Conteúdo |
|---|---|---|
| `dashboard_geral.png` | RQ1+RQ2+RQ3 | Painel único (grid 2x4) com as visões principais — pensado para apresentação |
| `rq1_tempo.png` | RQ1 | Tempo até o green (s, escala log) por tratamento — boxplot + pontos individuais |
| `rq1_tempo_por_integrante.png` | RQ1 | Mesmo gráfico, facetado por integrante (Ferreira/Santiago/Tavares) |
| `rq1_distribuicao_tempo.png` | RQ1 | Distribuição completa do tempo (KDE + pontos individuais/rug), escala log — mostra a forma da distribuição, não só mediana/IQR |
| `rq2_taxa_sucesso.png` | RQ2 | Taxa de sucesso (testes passando/total) por tratamento |
| `rq3_complexidade.png` | RQ3 | Complexidade ciclomática média (Radon `cc`) por tratamento |
| `rq3_loc.png` | RQ3 | LOC por tratamento (**controle obrigatório**, ver desenho do experimento) |
| `rq3_mi.png` | RQ3 | Índice de Manutenibilidade (opcional) por tratamento |
| `rq3_complexidade_vs_loc.png` | RQ3 | Dispersão complexidade × LOC, para checar se a diferença de complexidade não é só reflexo de LOC |
| `rq3_correlacao_metricas.png` | RQ3 | Heatmap de correlação (Pearson) entre LOC, complexidade e MI — checa multicolinearidade entre as métricas estruturais |
| `resumo_estatisticas.md` | RQ1+RQ2+RQ3 | Média, mediana, Q1, Q3, IQR e n por tratamento, para cada métrica |

Todos os gráficos usam a mesma paleta categórica de 2 cores (azul = Sem IA,
laranja = Com IA), validada quanto a daltonismo, e mostram a mediana de cada
grupo diretamente no gráfico (boxplot com mediana anotada; barra com valor no
topo). O heatmap de correlação usa uma paleta divergente à parte (azul↔vermelho
com meio-tom neutro em zero), porque ali a cor codifica força/direção de
correlação — uma variável de polaridade, diferente da identidade categórica
"com_ia vs sem_ia" dos demais gráficos (ver seção abaixo). Todo gráfico
individual traz um rodapé "Fonte: `<arquivo>.csv` — N=... (com_ia/sem_ia)",
no mesmo padrão de citação usado em material de referência de visualização de
dados (fonte + tamanho da amostra sempre visíveis, nunca implícitos).

## Por que um gráfico de distribuição além do boxplot (RQ1)

Um resumo como mediana/IQR colapsa toda a amostra em 3 números — com N pequeno
(9 trials/tratamento) isso pode esconder padrões que só aparecem olhando a
distribuição inteira (o clássico "a média mente quando a distribuição não é
normal": um resumo agregado pode parecer tranquilizador enquanto esconde
grupos com experiências bem diferentes). Por isso `rq1_distribuicao_tempo.png`
complementa `rq1_tempo.png`: mostra a curva de densidade (KDE) de cada
tratamento em escala log, com um "rug plot" marcando cada trial individual por
baixo da curva — nenhum dado fica escondido atrás do resumo estatístico. No
nosso caso as duas distribuições aparecem bem separadas e sem sobreposição
relevante (com_ia concentrado em segundos, sem_ia em minutos), o que reforça
visualmente a diferença de mediana já reportada em `resumo_estatisticas.md`.

## Boas práticas aplicadas (referência: material "Análise de Dados Aplicada à
Experimentação em Engenharia de Software", Grupo 1, PUC Minas)

O dashboard foi revisado para seguir as recomendações desse material sobre
estatística descritiva e escolha de gráficos:

- **Média ao lado da mediana, não no lugar dela.** `resumo_estatisticas.md`
  agora mostra as duas colunas para cada métrica. A distância entre elas é o
  próprio sinal de assimetria: no tempo (RQ1), a média fica acima da mediana
  nos dois tratamentos (mais no `com_ia`) — o padrão clássico de métricas de
  tempo em ES, que é exatamente por que a mediana/IQR (não a média) é a
  métrica primária da RQ1, conforme `docs/lab02/desenho-experimento.md`.
- **Distribuição completa além do resumo (RQ1).** Um resumo de 3 números pode
  esconder padrões que só aparecem olhando a forma inteira da distribuição —
  por isso `rq1_distribuicao_tempo.png` (KDE + pontos individuais) complementa
  o boxplot, sem depender só de mediana/IQR para contar a história do tempo.
- **Gráfico certo para cada tipo de relação:** boxplot para comparar
  distribuições entre grupos (RQ1/RQ3), barras para comparar duas categorias
  com poucos valores (RQ2), scatter para relação entre duas variáveis
  numéricas (RQ3 complexidade × LOC) e heatmap de correlação para checar
  multicolinearidade entre métricas antes de discuti-las isoladamente
  (RQ3 — `rq3_correlacao_metricas.png`, novo nesta revisão).
- **Cor com significado consistente.** Azul/laranja identifica sempre o
  mesmo tratamento em todo o dashboard (nunca cor por ranking). Já o heatmap
  de correlação usa uma paleta divergente separada (azul↔vermelho, meio-tom
  neutro em zero), porque ali a cor representa uma grandeza com polaridade
  (correlação negativa/positiva), não a identidade do tratamento — usar a
  mesma paleta categórica ali seria um erro de codificação.
- **Fonte e tamanho de amostra sempre visíveis.** Cada gráfico individual
  traz um rodapé citando o CSV de origem e o N por tratamento, para que o
  gráfico nunca seja lido fora do contexto de quantos dados o sustentam —
  relevante sobretudo aqui, com N pequeno (9 trials/tratamento).

