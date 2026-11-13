# Lab04 — roteiro oral de Ferreira

Respostas para seis perguntas do enunciado, ligadas ao cenário e aos dados reais
(#61), às simulações de Q1/Q2 (#64) e às seções finais do dashboard (#67). Cada
resposta cabe em cerca de 30 segundos e indica onde mostrar no dashboard. Os números
vêm de 10.000 repetições por combinação, semente 42 e α = 5%, salvo na pergunta 12.
Relatórios completos: [`cenario-dados.md`](cenario-dados.md), [`q1-q2.md`](q1-q2.md)
e [`q3-robustness.md`](q3-robustness.md).

O Santiago responde as perguntas 4, 8, 10 e 15
([roteiro](apresentacao-santiago.md)). Ficam sem responsável definido as perguntas
5, 6, 7, 9 e 11.

## Pergunta 1 — Qual é o cenário e o que H₀ e H₁ afirmam?

*Dashboard: seção 1.*

Comparamos o tempo até o merge de pull requests revisados por um bot de IA antes do
merge, como Copilot, Codex e CodeRabbit, com PRs sem esse tipo de revisão. Os PRs vêm de
repositórios open source populares que usam bot em parte dos PRs. H₀ diz que o tempo é
o mesmo nos dois grupos: para o Welch, médias iguais; para o Mann–Whitney, distribuições
iguais. H₁ diz que os tempos diferem, em qualquer direção.

## Pergunta 2 — O teste é unicaudal ou bicaudal? Por quê?

*Dashboard: G2, com a região de rejeição nas duas caudas.*

Bicaudal, com α = 5%. O bot pode acelerar o merge, porque aponta problemas cedo, ou
atrasá-lo, porque gera mais rodadas de ajuste, e não tínhamos motivo para apostar numa
direção antes de ver os dados. Escolher a cauda depois de olhar os resultados dobraria,
na prática, o erro tipo I.

## Pergunta 3 — Como os dados reais foram coletados e o que mostraram sobre a forma?

*Dashboard: seção 1 e G1, com o eixo em escala log.*

Usamos um script próprio na API GraphQL do GitHub. Dos 500 repositórios públicos com
mais estrelas, 78 usavam bot em parte dos PRs, e sorteamos 60 com semente fixa: 30 para
cada grupo, com um PR por repositório, para que as observações fossem independentes. O
tempo é a diferença entre o merge e a criação do PR, só com autores humanos e PRs abertos
por pelo menos 10 minutos, para o bot ter tempo de revisar. Uma auditoria pela API REST
confirmou os 60 PRs. A forma é muito assimétrica: com bot, a mediana é 40,4 h e a média,
384,5 h. A normalidade é rejeitada em horas (p < 0,001), mas não em log(horas) (p = 0,96
e 0,38), por isso usamos a lognormal.

## Pergunta 12 — Se usassem α = 0,01, o que mudaria no G3 e no G4?

*Dashboard: G3 e G4. O α da barra lateral muda só o G2 e a seção 6; G3 e G4 vêm dos
resultados pré-calculados com α = 5%. Para mostrá-los com α = 1%, rode
`python -m lab04 --alpha 0.01`, que sobrescreve os resultados versionados; depois,
`python -m lab04` volta a α = 5%.*

No G3, a linha de referência desce para 1% e as taxas descem junto: com 30 PRs por
grupo, o Mann–Whitney vai de 5,1% para 1,0%, e o Welch, de 1,5% para 0,06%, ou seja,
fica ainda mais conservador. No G4, todas as curvas de poder caem: no maior efeito
simulado (medianas 2,72× maiores, n = 30), o Mann–Whitney vai de 32,4% para 13,4%, e o
Welch, de 6,2% para 0,5%. Para o efeito observado nos dados reais, nem 240 PRs por grupo
bastariam para 80% de poder. É a troca de sempre: menos falsos positivos, mais falsos
negativos.

## Pergunta 13 — A simulação confirmou o que o grupo esperava?

*Dashboard: seções 4, 5 e 7.*

Sim. Antes de simular, registramos que o Mann–Whitney ficaria perto de 5% de erro tipo
I, o Welch provavelmente abaixo disso, e que o Mann–Whitney teria mais poder. Na Q1, o
Welch ficou entre 0,8% e 3,0% e o Mann–Whitney entre 4,6% e 5,2%. Na Q2, o Mann–Whitney
teve mais poder em todos os efeitos e tamanhos amostrais, por exemplo 32,4% contra 6,2%
com n = 30 e medianas 2,72× maiores. A explicação está na cauda: com σ de log em torno de
2,4, poucos valores extremos inflam a média e a variância e deixam o t pequeno, enquanto
os postos ignoram a magnitude. O que surpreendeu foi o tamanho da vantagem e o fato de os
outliers da Q3 quase não mudarem o quadro.

## Pergunta 14 — Nos dados reais, os testes concordam? O efeito tem importância prática?

*Dashboard: seção 6.*

Concordam: nenhum dos dois rejeita H₀ (Welch p = 0,445; Mann–Whitney p = 0,429). O efeito
estimado é pequeno: g de Hedges de 0,20, um PR com bot é mais lento que um sem bot em 56%
dos pares, e a diferença típica (Hodges–Lehmann) é de 7,4 h, frente a medianas de 40,4 h
e 34,6 h, o que tem pouca importância prática. Mas o intervalo da diferença de médias vai
de −270 h a +604 h, e com 30 PRs por grupo o poder para detectar um efeito desse tamanho é
só 18%. Portanto, não rejeitar H₀ não prova que o bot não faz diferença; mostra que a
amostra é pequena para detectá-la.
