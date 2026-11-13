# Lab04 — roteiro oral de Tavares

Respostas para as perguntas 5, 6, 7, 9 e 11, as que tratam dos dois testes, do G2, do
G3 e da violação de pressupostos. Cada resposta tem de 66 a 75 palavras (25 a 30 segundos falados) e indica
onde mostrar no dashboard. Os números vêm de 10.000 repetições, semente 42, α = 5% e
n = 30 por grupo; os do G2 são do exemplo simulado que o dashboard abre por padrão
(semente 42, 30 PRs por grupo). Relatórios completos: [`q1-q2.md`](q1-q2.md) e
[`q3-robustness.md`](q3-robustness.md).

## Pergunta 5 — O que cada teste compara de fato?

*Dashboard: seção 3, os dois painéis do G2.*

O t de Welch compara **médias**: a diferença entre as médias dividida pelo erro-padrão, sem supor
variâncias iguais. O Mann–Whitney compara **postos**: junta os 60 PRs, ordena do mais rápido ao mais
lento e vê se um grupo concentra as posições altas; é a chance de um PR de um grupo ser mais lento
que um do outro. Por isso extremos pesam no Welch e quase nada no Mann–Whitney.

## Pergunta 6 — No G2, o que é a distribuição da estatística sob H₀ e por que a região de rejeição fica onde fica?

*Dashboard: G2, região sombreada clara nas duas caudas.*

É a distribuição que a estatística teria **se não houvesse diferença**. Para o Welch, uma t de Student
com 31 graus de liberdade; para o Mann–Whitney, U obtido por 10.000 permutações, centrado em 450. A
rejeição fica nas **duas caudas**, onde os valores são raros sob H₀ e porque H₁ diz "diferem": 2,5% de
cada lado, t além de ±2,04 e U fora de 318 a 584. Somam os 5% de erro tipo I aceitos.

## Pergunta 7 — O que significa o p-valor do exemplo do G2? E o que ele não significa?

*Dashboard: G2, área escura sob a curva e linha tracejada da estatística observada.*

No exemplo, t = −0,75 com p = 0,46 no Welch, e U = 520 com p = 0,31 no Mann–Whitney. O p-valor é a
probabilidade de uma estatística **tão extrema quanto a observada, ou mais, se H₀ for verdadeira**; é a
área escura. Como passa de 5%, não rejeitamos. Ele **não** é a probabilidade de H₀ ser verdadeira, nem
mede o tamanho do efeito, e p alto não prova que os grupos são iguais.

## Pergunta 9 — No G3, algum teste se afastou de 5%? Liberal ou conservador, e por quê?

*Dashboard: seção 4, barras do G3 e a linha tracejada em 5%.*

O Welch se afastou: 1,5% na referência e 1,1% com outliers, bem abaixo de 5%, ou seja, **conservador**.
O Mann–Whitney ficou perto: 4,7% e 4,4%, a cerca de meio ponto de 5%. Com σ de log perto de 2,4, poucos
valores extremos inflam a variância e deixam o t pequeno, então o Welch quase nunca rejeita. Os postos
limitam essa influência. Nenhum dos dois foi liberal.

## Pergunta 11 — Que violação de pressuposto vocês simularam e por que ela afeta mais um teste?

*Dashboard: seção 4 (outliers, G3) e seção 5 (assimetria, tabela de σ).*

Duas violações: **outliers**, com 5% dos tempos multiplicados por 20, e **assimetria** crescente, com σ de
log de 0,1 até 2,43, o valor real. O Welch usa média e variância, dominadas por um valor extremo; o
Mann–Whitney usa postos, em que o extremo conta só como "o maior". Com σ = 2,43, o poder é 8,7% no Welch e
45,1% no Mann–Whitney; com σ = 0,1, ficam próximos: 47,9% contra 45,5%.

---

**Se o professor insistir ou perguntar além do roteiro**

- **Os outliers da Q3 mudaram pouco o quadro**, porque a base lognormal já é extremamente
  assimétrica: o Welch foi de 1,5% para 1,1% de erro tipo I e o Mann–Whitney de 4,7% para
  4,4%. Quem mostra o efeito claro da assimetria é a tabela de σ, não a contaminação.
- **O U do G2 tem dois p-valores no dashboard:** 0,31 pela permutação, que é o que o G2
  desenha, e 0,30 pela aproximação normal, que o scipy devolve. A conclusão é a mesma.
- **O exemplo do G2 não é o dado real.** É um conjunto simulado das duas lognormais
  ajustadas, só para ilustrar o teste. A comparação nos dados reais está na seção 6 (p = 0,445
  no Welch e 0,429 no Mann–Whitney).
