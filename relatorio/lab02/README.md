# Relatório final do Lab02

Responsável: Gabriel Ferreira Amaral (`Druitti`). Issue #40.

- `Lab02_Relatorio_Final.pdf`: versão para leitura e entrega.
- `Lab02_Relatorio_Final.docx`: versão editável.
- `roteiro_apresentacao.md`: roteiro sugerido de cinco minutos (ajustável ao tempo da turma).
- `figuras/`: gráficos em PNG de 300 dpi e SVG vetorial.
- `resultados_relatorio.json`: valores usados, testes, outliers e hashes dos CSVs.

## Dados e escolhas dos gráficos

Os dados vêm de `lab02/data/trials.csv` e `lab02/data/static_metrics.csv`.
As 18 medições de CC, LOC e SLOC são conferidas com Radon nas soluções preservadas
em `lab02/trials/<participante>/<kata>/kata.py`, sem depender dos caminhos genéricos
de `arquivo` no CSV. Os dados de coleta não são regravados pelo gerador.

O gráfico de tempo liga medianas da mesma pessoa em escala linear, com valores
exatos e unidade. Em RQ2, a escala percentual completa mostra que todos os trials
coincidem em 100%. Em RQ3, os pontos mostram os nove trials de cada tratamento;
as faixas indicam Q1–Q3 e os traços pretos, as medianas. O deslocamento horizontal
dos pontos só revela sobreposições. As cores e formas mantêm o mesmo significado
nas três figuras: laranja/círculo = com IA; azul/quadrado = sem IA.

Todas as figuras trazem fonte, unidade e tamanho da amostra nas legendas do
relatório. Não usamos curvas de densidade para inferir formas de distribuição
a partir de nove observações, nem barras de média que escondam os dados.

## Procedência dos tempos

O README do dashboard identifica `trials.csv` como fonte de RQ1/RQ2. O commit
`b09955d` alterou os tempos sem IA de Ferreira (K4, K5 e K6) de
19,50 / 22,08 / 21,94 s para 426,47 / 473,86 / 521,25 s. Não foi localizada uma
explicação específica de remedição nesse README ou nas issues dos trials.
O relatório usa o CSV atual e declara essa limitação, sem apresentar a mudança
como nova medição verificada. O script não altera tempos ou timestamps.

Os quartis são calculados por interpolação linear inclusiva (tipo 7), igual ao
dashboard atual. Isso difere da convenção do relatório inicial de RQ3.

## Reprodução

Ambiente validado: Python 3.12. Instale as dependências na raiz:

```bash
python -m pip install -r relatorio/lab02/requirements.txt
python scripts/gerar_relatorio_lab02.py
python lab02/scripts/analyze_rq1_rq2.py
python -m pytest lab02/scripts lab02/katas/reference -q
```

O gerador produz DOCX, gráficos e JSON. Para exportar o PDF a partir do DOCX,
use Word/LibreOffice ou o comando abaixo em um ambiente com LibreOffice:

```bash
soffice --headless --convert-to pdf --outdir relatorio/lab02 relatorio/lab02/Lab02_Relatorio_Final.docx
```

Confira a paginação após exportar: a versão entregue foi renderizada e revisada
visualmente em quatro páginas. RQ1/RQ2 são integradas da issue #35; RQ3, da
análise de Santiago; o dashboard da issue #39 permanece como artefato separado.
