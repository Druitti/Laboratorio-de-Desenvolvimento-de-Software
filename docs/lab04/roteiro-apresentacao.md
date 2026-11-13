# Lab04 — roteiro da apresentação (7 minutos, 15 perguntas)

Roteiro mestre: quem fala, em qual seção do dashboard e em quanto tempo. O texto de cada
resposta está nos roteiros individuais:
[Ferreira](apresentacao-ferreira.md) (1, 2, 3, 12, 13, 14),
[Santiago](apresentacao-santiago.md) (4, 8, 10, 15) e
[Tavares](apresentacao-tavares.md) (5, 6, 7, 9, 11).
Dashboard: https://dashboardpy-enwxyjy2g2xvwpvcjed45m.streamlit.app/ (local:
`python -m lab04`, em `http://localhost:8501`).

## Regras do enunciado que o roteiro cumpre

- Até **7 minutos**; respostas curtas, cerca de 30 s cada; tudo **usando o dashboard**.
- Perguntas divididas entre os integrantes, **cada um responde a pelo menos 4**; o professor
  pode chamar qualquer um para qualquer pergunta. Por isso, todos devem conhecer as 15.
- Nesta divisão: Ferreira 6, Santiago 4, Tavares 5. **Se o grupo tem um quarto integrante**,
  ele precisa assumir pelo menos 4: a sugestão é tirar uma pergunta de cada um dos três e
  completar com a pergunta que sobrar do grupo (por exemplo, 2, 12, 14 do Ferreira e 9 do Tavares).

## Tempo: 7 min = 420 s

15 respostas de 25 s somam 375 s; sobram cerca de 45 s para as 9 trocas de voz (~4 s cada). **Meta de 25 s por resposta**, nunca mais de 30 s. Quem responde já está
com a seção aberta; quem vai falar a seguir rola a tela enquanto o colega termina.

## Ordem sugerida: segue as seções do dashboard, de cima para baixo

| # | Pergunta | Seção do dashboard | Quem | Tempo |
|---|---|---|---|---|
| 1 | Cenário, H₀ e H₁ | 1. Cenário | Ferreira | 25 s |
| 2 | Uni ou bicaudal | 1 → G2 (caudas) | Ferreira | 20 s |
| 3 | Coleta e forma dos dados reais | 1 e G1 | Ferreira | 25 s |
| 4 | Dados reais → parâmetros da simulação | 2. Os dados (G1) | Santiago | 25 s |
| 5 | O que cada teste compara | 3. Como os testes funcionam | Tavares | 25 s |
| 6 | Distribuição sob H₀ e região de rejeição | 3 (G2) | Tavares | 25 s |
| 7 | Significado do p-valor do exemplo | 3 (G2) | Tavares | 25 s |
| 8 | Erro tipo I e II, qual é mais grave | 4 (antes do G3) | Santiago | 25 s |
| 9 | G3: algum teste fugiu de 5%? | 4. Erro tipo I (G3) | Tavares | 25 s |
| 11 | Violação de pressuposto simulada | 4 e 5 (outliers e σ) | Tavares | 25 s |
| 10 | G4: qual tem mais poder? | 5. Poder (G4) | Santiago | 25 s |
| 12 | E se α = 1%? | 4 e 5 (G3 e G4) | Ferreira | 25 s |
| 14 | Dados reais: concordam? efeito prático? | 6. Dados reais | Ferreira | 25 s |
| 13 | A simulação confirmou o esperado? | 7. Conclusão | Ferreira | 25 s |
| 15 | Recomendação e limitação | 7. Conclusão | Santiago | 25 s |

Total: **370 s** de resposta (14 × 25 s + 20 s), mais cerca de 36 s de trocas = **~406 s**, ou 6 min 46 s,
com 14 s de folga. É apertado: qualquer resposta de 35 s estoura os 7 min.

## Tamanho das respostas: o que cabe em 25 s

Falando em ritmo normal (cerca de 150 palavras por minuto), **25 s são ~60 a 65 palavras e 30 s,
~75**. Contagem atual dos roteiros (sem a linha "Dashboard"):

| Quem | Palavras por resposta | Situação |
|---|---|---|
| Tavares (5, 6, 7, 9, 11) | 66 a 75 | Dentro de 30 s (5 e 9 cabem em 25 s) |
| Santiago (4, 8, 10, 15) | 64 a 82 | Dentro, exceto a 10, que passa um pouco |
| Ferreira (1, 2, 3, 12, 13, 14) | 51 a 125 | **Passam:** 3, 12, 13 e 14 têm 99 a 125 palavras (40 a 50 s) |

Somando tudo, os roteiros do Ferreira estouram os 7 min. Antes de ensaiar, o Ferreira deve
cortar as perguntas 3, 12, 13 e 14 para ~75 palavras, mantendo a frase-chave abaixo e os
dois ou três números principais.

## Frases-chave (a primeira frase de cada resposta)

1. Comparamos o tempo até o merge de PRs com e sem revisão de bot; H₀ diz que o tempo é igual, H₁ que difere.
2. Bicaudal: o bot pode acelerar ou atrasar, e não apostamos numa direção.
3. API do GitHub, 60 PRs, 30 por grupo, um por repositório; forte assimetria, normal só em log.
4. Os tempos são positivos e assimétricos, então a simulação usa lognormal com μ e σ de cada grupo.
5. Welch compara médias; Mann–Whitney compara postos.
6. É o que a estatística valeria sem diferença; rejeitamos nas duas caudas, 2,5% em cada.
7. É a probabilidade de uma estatística tão extrema se H₀ for verdadeira, não a de H₀ ser verdadeira.
8. Tipo I: dizer que o bot muda o tempo quando não muda; tipo II: não ver um efeito que existe.
9. Welch ficou conservador (1,5%); Mann–Whitney ficou perto de 5% (4,7%).
10. Mann–Whitney tem mais poder em todos os efeitos, mas o poder é baixo com n = 30.
11. Outliers (5% × 20) e assimetria crescente; o Welch usa média e variância, que os extremos dominam.
12. Com α = 1%, as taxas do G3 caem para perto de 1% e todas as curvas do G4 descem.
13. Sim: Mann–Whitney perto de 5% e mais poderoso; o que surpreendeu foi o tamanho da vantagem.
14. Os dois não rejeitam (p = 0,445 e 0,429); o efeito é pequeno e o poder é de 18%.
15. Recomendamos o Mann–Whitney; a principal limitação é o n pequeno e o desenho observacional.

## Antes de entrar (checklist)

- [ ] Abrir a URL do dashboard **uns minutos antes**, para o app acordar, e conferir as 7 seções.
- [ ] Deixar também o dashboard local aberto (`python -m lab04`) como plano B.
- [ ] Barra lateral com **α = 5%, semente 42, 30 observações por grupo** (os números dos roteiros partem disso).
- [ ] Uma pessoa controla a tela (sugestão: quem fala as perguntas 5 a 11, Tavares) e os outros só indicam a seção.
- [ ] Pergunta 12: o α da barra lateral muda só o G2 e a seção 6. Para o G3 e o G4 com α = 1% é
  preciso rodar `python -m lab04 --alpha 0.01` antes; **não** faça isso na hora. Responda com os
  números do roteiro do Ferreira e volte depois com `python -m lab04`.
- [ ] Cada integrante ensaia as 15 respostas, não só as suas, e cronometra.

## Pontos delicados para a banca

- **O Welch tem poder muito baixo** (6,2% no maior efeito simulado com n = 30): é o resultado
  mais provável de gerar pergunta. A explicação é a cauda: com σ de log ≈ 2,4, valores extremos
  inflam a variância. A vantagem do Mann–Whitney some quando os dados são quase simétricos (σ ≤ 0,5).
- **Nenhum teste rejeita H₀ nos dados reais** (p ≈ 0,43–0,45): não dizer que "o bot não faz
  diferença"; dizer que a amostra é pequena (poder de 18%, seriam necessários 240 PRs por grupo).
- **Dados observacionais:** não há causalidade, e o tamanho dos PRs difere entre os grupos.
- **Os outliers da Q3 quase não mudaram o quadro**, porque a base já é muito assimétrica.
