# Roteiro sugerido de apresentação

Tempo de referência: 5 minutos. O enunciado não fixa a duração da apresentação;
confirme o limite com o professor. O roteiro seleciona o essencial do relatório.

## 0min a 1min — Objetivo e método

“Comparamos programação com e sem ChatGPT em seis katas Python. Foram três
participantes, com três tarefas por tratamento para cada um: 18 trials no total.
Medimos tempo até passar nos testes, taxa de sucesso e complexidade com LOC.
Cada pessoa foi comparada consigo mesma, usando suas medianas por tratamento.”

Mostre a página 1. Destaque que são três pares para inferência, não nove.

## 1min a 2min15 — Tempo

Mostre a figura 1 na página 2 e explique uma linha: cada extremidade corresponde
à mediana dos três trials da mesma pessoa. Os tempos registrados são menores
com IA para todos. O Wilcoxon deu p = 0,125; não houve significância a 5%.
Com três pares, até o resultado mais favorável tem p mínimo de 0,125.

Não diga que a IA “comprovadamente acelerou” ou generalize a razão de tempos.

## 2min15 a 2min45 — Sucesso nos testes

Na figura 2, ambos os tratamentos ficaram em 100%. Como o cronômetro para no
green, houve efeito teto. Não foi possível avaliar redução de defeitos.
Passar nos testes não significa que o código não tenha outros defeitos.

## 2min45 a 3min45 — Estrutura

Mostre a figura 3 na página 3. Cada ponto é um trial. A mediana de complexidade
é 4 em ambos, enquanto LOC é 23 com IA e 17 sem IA. Código mais longo não
significa automaticamente código mais complexo. As medianas de CC por pessoa
também coincidem, então o teste não tem diferenças não nulas para comparar.
A duplicação não foi medida.

## 3min45 a 5min — Limitações e conclusão

Mostre a página 4. Destaque três participantes, dificuldade das tarefas e
procedência dos tempos. O CSV atual contém uma alteração de três durações sem
IA, registrada no histórico, sem justificativa específica de remedição no
README; o relatório declara esse limite. Os valores extremos foram mantidos.

“Observamos tempos menores com IA nos registros, mas a amostra não sustenta
uma conclusão estatística. Sucesso final e complexidade mediana não distinguiram
os tratamentos. Uma próxima coleta precisa de mais participantes e de registros
verificáveis do processo, incluindo falhas antes do green.”

Se houver apenas 3 minutos, reserve 30 s ao método, 60 s ao tempo, 20 s ao
sucesso, 40 s à estrutura e 30 s à conclusão.
