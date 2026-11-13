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

## Pergunta 10 — Qual teste teve mais poder? Isso muda com o tamanho do efeito?

No cenário Q3 com outliers, Mann–Whitney teve mais poder em todos os efeitos
avaliados. Para uma razão simulada de medianas de 1,49×, o poder foi 8,2% para
Mann–Whitney e 1,8% para Welch; em 2,72×, foi 31,1% e 4,6%, respectivamente.
O poder aumenta com o efeito, mas ainda é baixo em `n=30`. Com outliers, o erro
tipo I estimado foi 4,4% para Mann–Whitney e 1,1% para Welch, frente a alfa de
5%; a diferença de poder deve ser lida junto com esse controle.

## Pergunta 11 — Que violação de pressuposto vocês simularam e por que ela afeta mais um teste?

*Dashboard: seção 4 (outliers, G3) e seção 5 (assimetria, tabela de σ).*

Duas violações: **outliers**, com 5% dos tempos multiplicados por 20, e **assimetria** crescente, com σ de
log de 0,1 até 2,43, o valor real. O Welch usa média e variância, dominadas por um valor extremo; o
Mann–Whitney usa postos, em que o extremo conta só como "o maior". Com σ = 2,43, o poder é 8,7% no Welch e
45,1% no Mann–Whitney; com σ = 0,1, ficam próximos: 47,9% contra 45,5%.

## Pergunta 15 — Qual teste recomendam e qual é a principal limitação?

Para comparar a tendência de tempos muito assimétricos, recomendamos Mann–Whitney
como principal e Welch como complemento quando a pergunta for especificamente
sobre médias. A recomendação é provisória ao modelo e à amostra: Q3 mostrou poder
limitado com 30 observações por grupo. Além disso, os dados são observacionais e
os grupos diferem no tamanho dos PRs, então não permitem atribuir causalidade ao
uso de bot.
