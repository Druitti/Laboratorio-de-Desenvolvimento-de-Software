# Lab04 — roteiro oral de Santiago

Respostas concisas para quatro perguntas do enunciado. Os números de Q3 foram
gerados com 10.000 repetições, `n=30` por grupo, alfa de 5% e semente 42; veja
[`q3-robustness.md`](q3-robustness.md) para o relatório completo.

## Pergunta 4 — Como os dados reais ajudaram a escolher os parâmetros da simulação?

Os tempos reais são positivos e muito assimétricos. Por isso a simulação usa uma
lognormal e estima média e desvio-padrão de `log(horas)` separadamente por grupo.
Na amostra, os parâmetros são μ=3,676 e σ=2,308 para PRs com bot, e μ=3,002 e
σ=2,537 para PRs sem bot. A semente 42 torna a amostra simulada repetível. O
ajuste reproduz a forma observada, mas a cauda é instável com apenas 30 PRs por
grupo.

## Pergunta 8 — O que são erro tipo I e tipo II? Qual seria mais grave?

Erro tipo I é concluir que há diferença quando H₀ é verdadeira; erro tipo II é
deixar passar uma diferença real. Um falso positivo poderia levar o grupo a
recomendar um bot com base numa associação que não existe. Um falso negativo
poderia ocultar um benefício ou custo verdadeiro. Qual pesa mais depende da
decisão; nenhum teste observacional prova que o bot causou a diferença.

## Pergunta 10 — Qual teste teve mais poder? Isso muda com o tamanho do efeito?

No cenário Q3 com outliers, Mann–Whitney teve mais poder em todos os efeitos
avaliados. Para uma razão simulada de medianas de 1,49×, o poder foi 8,2% para
Mann–Whitney e 1,8% para Welch; em 2,72×, foi 31,1% e 4,6%, respectivamente.
O poder aumenta com o efeito, mas ainda é baixo em `n=30`. Com outliers, o erro
tipo I estimado foi 4,4% para Mann–Whitney e 1,1% para Welch, frente a alfa de
5%; a diferença de poder deve ser lida junto com esse controle.

## Pergunta 15 — Qual teste recomendam e qual é a principal limitação?

Para comparar a tendência de tempos muito assimétricos, recomendamos Mann–Whitney
como principal e Welch como complemento quando a pergunta for especificamente
sobre médias. A recomendação é provisória ao modelo e à amostra: Q3 mostrou poder
limitado com 30 observações por grupo. Além disso, os dados são observacionais e
os grupos diferem no tamanho dos PRs, então não permitem atribuir causalidade ao
uso de bot.
