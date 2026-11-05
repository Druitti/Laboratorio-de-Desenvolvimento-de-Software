# Lab04S01 — cenário, hipóteses e dados reais (#61)

Project v2: https://github.com/users/Druitti/projects/5

## Cenário e pergunta

Par P1 do enunciado, t de Welch × Mann–Whitney: comparar o tempo até o merge de pull
requests com e sem bot de revisão, em dois grupos independentes.

> Em repositórios open source populares que usam bots de revisão em parte dos PRs,
> o tempo até o merge difere entre PRs revisados por um bot e PRs sem essa revisão?

- **Unidade:** um PR mergeado de autor humano.
- **Variável:** horas entre a criação e o merge (`value` em `lab04/data/real_prs.csv`).
- **`with_review_bot`:** ao menos uma review de um bot da lista, enviada antes do merge.
- **`without_review_bot`:** nenhuma review de conta do tipo Bot e nenhum comentário de
  bot da lista.

A pergunta é sobre associação. Os dados são observacionais e não permitem concluir
que o bot causa a diferença.

## Hipóteses e par de testes

O nível de significância é 5%, nos dois testes. O teste é bilateral porque o bot pode
tanto acelerar o merge (antecipa correções) quanto atrasá-lo (gera mais rodadas).

| Teste | H0 | H1 |
|---|---|---|
| t de Welch | as médias dos tempos são iguais | as médias diferem |
| Mann–Whitney | as distribuições dos tempos são iguais | um grupo tende a ter tempos maiores que o outro |

## Fonte e método

Fonte: API GraphQL v4 do GitHub. O coletor é `lab04/collect_real_data.py`, e todos os
parâmetros estão em `lab04/config.json`. Como pede o enunciado, nenhum dado, resultado ou
código de outros laboratórios é usado.

1. **Quadro:** os 500 repositórios públicos com mais estrelas, entre os não arquivados,
   que não são fork e receberam push desde 2026-01-01.
2. **PRs:** mergeados, criados em [2026-01-01, 2026-07-01) e mergeados antes de
   2026-11-01; todo PR tem ao menos quatro meses de seguimento. Para cada repositório
   são lidos até os 100 mais recentes.
3. **Bots:** lista de 16 bots de revisão de código por IA em `config.json`, definida vendo
   apenas quem revisa, sem calcular tempos de merge. Neste quadro, os bots que mais
   revisam já estavam nela. PR só com review de bot fora da lista é excluído, então esses
   bots não alteram nenhum dos grupos. O tipo da conta é conferido, porque logins como
   `claude` e `cursor` também podem ser de pessoas.
4. **Exclusões:** autor bot ou removido; merge em menos de 10 minutos; PR ambíguo (review
   de bot fora da lista, review de bot da lista após o merge, comentário de bot da lista
   sem review de bot antes do merge, ou conta removida); mais de 100 reviews ou comentários.
5. **Elegibilidade:** ao menos 5 PRs em cada grupo, entre os PRs lidos do repositório.
6. **Sorteio (semente 42):** 60 repositórios elegíveis, 30 para cada grupo, e um PR de
   cada. Um repositório nunca alimenta os dois grupos.

O enunciado sugere coletar PRs de um repositório. Preferimos um PR por repositório porque
isso sustenta a independência exigida pelos dois testes e impede que um único projeto
determine a forma da distribuição. Em troca, as diferenças entre projetos entram na
variância, o que reduz o poder.

### Funil

| Etapa | Quantidade |
|---|---:|
| Repositórios no quadro | 500 |
| Repositórios elegíveis | 78 |
| Repositórios sorteados | 60 |
| PRs lidos | 30.513 |
| Com bot | 5.761 |
| Sem bot | 16.622 |
| Excluídos: autor bot ou removido | 3.383 |
| Excluídos: merge em menos de 10 min | 2.770 |
| Excluídos: ambíguos | 1.960 |
| Excluídos: reviews ou comentários truncados | 17 |

O detalhe por repositório está em `lab04/data/real_funnel.csv`.

### Regra dos 10 minutos

Um PR mergeado antes de o bot ter tempo de responder cai em "sem bot" por construção, e
não por ter dispensado a revisão (viés de tempo imortal). A regra veio de uma amostra
exploratória descartada, que tinha PRs de 9 segundos no grupo sem bot. Essa amostra usava
outro quadro, trocado para atender à independência entre laboratórios. A amostra atual
já foi coletada com a regra.

O limiar vem da latência dos bots, e não da diferença entre os grupos. Medindo neste
quadro, sem aplicar a regra:

- entre as 6.024 primeiras reviews de bot, a mediana é 4,3 min, e 74,8% chegam em até 10 min;
- os merges em menos de 10 min são 4,4% dos PRs com bot e 10,9% dos PRs sem bot.

## Resumo dos dados reais

| Horas até o merge | Com bot (n = 30) | Sem bot (n = 30) |
|---|---:|---:|
| Média | 384,5 | 217,6 |
| Mediana | 40,4 | 34,6 |
| Q1 – Q3 | 11,3 – 140,9 | 2,2 – 71,1 |
| Desvio-padrão | 1.055,5 | 542,9 |
| Mínimo – máximo | 0,2 – 5.361,8 | 0,2 – 2.658,1 |
| Assimetria | 4,07 | 3,65 |
| Curtose em excesso | 18,05 | 14,62 |
| Shapiro–Wilk em horas (p) | < 0,001 | < 0,001 |
| Shapiro–Wilk em log(horas) (p) | 0,961 | 0,382 |
| Linhas alteradas (mediana) | 84,5 | 200,5 |
| Arquivos alterados (mediana) | 3 | 3 |

Razão entre as variâncias em horas: 3,8. Brown–Forsythe: p = 0,451 em horas e
p = 0,551 em log(horas). Resumo completo: `lab04/data/real_summary.json`.

Bots no grupo com bot (um PR pode ter mais de um): Copilot 23, Codex 3, CodeRabbit 2,
cubic 2 e Claude 1.

## Geração dos dados simulados

Cada grupo segue uma lognormal, com parâmetros estimados da amostra real
(`lab04/simulation.py`, #62): μ é a média e σ é o desvio-padrão amostral de log(horas).

| Grupo | μ | σ | Mediana da lognormal, e^μ (h) | Mediana real (h) |
|---|---:|---:|---:|---:|
| Com bot | 3,676 | 2,308 | 39,5 | 40,4 |
| Sem bot | 3,002 | 2,537 | 20,1 | 34,6 |

A lognormal foi escolhida porque os tempos são positivos e muito assimétricos, e porque a
normalidade não é rejeitada em log(horas) nos dois grupos, embora seja rejeitada com folga
em horas.

Estes parâmetros descrevem cada grupo como foi observado, com o efeito que a amostra
contém. Em Q1, com H0 verdadeira, os dois grupos precisam vir da mesma distribuição (#64).

## Por que Welch e Mann–Whitney

| O que os dados mostram | Consequência |
|---|---|
| Cada PR vem de um repositório diferente, sem pareamento | Testes para grupos independentes; t pareado e Wilcoxon pareado não se aplicam |
| Razão de variâncias de 3,8; Brown–Forsythe não rejeita a igualdade, mas tem pouco poder com n = 30 | Não há base para supor variâncias iguais, como faz o t de Student; Welch não precisa dessa suposição |
| Forte assimetria, e média muito acima da mediana (384,5 h contra 40,4 h com bot) | A média é puxada pela cauda; vale comparar um teste de médias com um teste de postos, que não usa a magnitude dos extremos |
| Normalidade rejeitada em horas, com n = 30 | Welch depende da aproximação pelo teorema central do limite, que pode falhar com cauda tão pesada; a S02 mede esse efeito |

Os dois testes respondem a perguntas diferentes: Welch trata da média, ligada à espera
total acumulada; Mann–Whitney trata de qual grupo tende a ter tempos maiores. Por ser
baseado em postos, Mann–Whitney dá o mesmo resultado em horas e em log(horas). Ele só
pode ser lido como diferença de localização se os formatos forem semelhantes, o que os
desvios em log(horas) apoiam, sem comprovar.

O t de Welch sobre log(horas) foi deixado fora do par porque compara médias geométricas,
e não a média em horas.

## Recomendação prévia

Registrada antes das simulações de Q1–Q3 e antes de aplicar os testes aos dados reais.
É uma proposta que o grupo deve confirmar, e a conclusão em #67 deve compará-la com os
achados.

- **Teste que esperamos que se saia melhor:** Mann–Whitney, como teste principal para
  tempo até o merge, com Welch como complemento quando a pergunta for sobre a média.
- **Por quê:** com σ acima de 2, valores extremos dominam a média e a variância amostral.
  Isso prejudica Welch, enquanto os postos não dependem da magnitude dos extremos.
- **Expectativa:** com distribuições iguais, Mann–Whitney deve ficar perto de 5% de erro
  tipo I, e Welch possivelmente abaixo disso. Mann–Whitney também deve ter mais poder.
- **A recomendação mudaria se:** Welch alcançasse poder igual ou maior com erro tipo I
  controlado, ou se Mann–Whitney inflasse o erro tipo I com formatos diferentes (Q3).

## Limitações

- **Sem causalidade:** o uso do bot pode depender do PR. O tamanho, por exemplo, difere
  entre os grupos (mediana de 84,5 contra 200,5 linhas).
- **Viés de tempo imortal residual:** a regra dos 10 minutos remove o caso extremo, mas
  uma review tardia ainda exige que o PR continue aberto.
- **Somente PRs mergeados:** PRs abandonados ou ainda abertos não entram.
- **Tempo em draft:** é contado, pois o relógio começa na criação do PR.
- **PRs não filtrados:** merges feitos pelo próprio autor, PRs de release e reverts
  permanecem na amostra.
- **Generalização:** vale para repositórios populares que usam bot nos dois modos (78 de
  500). O quadro inclui listas e material educacional, com fluxo de revisão diferente do
  de um software: o maior tempo do grupo com bot (5.361,8 h) é de `github/gitignore`.
- **Concentração recente:** 247 dos 500 repositórios têm mais de 100 PRs na janela, e
  a leitura pega os mais recentes. Por isso, 33 dos 60 PRs são de junho de 2026 (14 com
  bot e 19 sem bot).
- **Presença não é qualidade:** não se avalia o conteúdo da review. O Copilot aparece em
  23 dos 30 PRs com bot, então o grupo reflete principalmente esse produto.
- **Lista manual de bots:** bots fora da lista que só comentam continuam no grupo sem bot.
- **Parâmetros instáveis:** com n = 30 e σ acima de 2, a cauda da lognormal ajustada é
  muito sensível à amostra. Ela também pode gerar tempos maiores do que a coleta permite
  observar, cerca de 7.300 h entre o início da janela e o corte.

## Verificação

Os 60 PRs foram auditados pela API REST, um caminho independente do GraphQL da coleta,
comparando datas, autor, reviews e comentários. Não houve divergência. A auditoria foi
feita uma vez e não faz parte dos comandos abaixo.

## Reprodução

Na raiz do repositório:

```bash
python -m pip install -r lab04/requirements.txt pytest
```

Valida o CSV e regenera o resumo, sem usar a rede:

```bash
python -m lab04.real_data
```

Executa os testes, incluindo a validação do CSV versionado:

```bash
python -m pytest lab04/tests -q
```

Refaz a coleta (leva cerca de 20 minutos, requer `gh auth login` e sobrescreve o CSV):

```bash
GITHUB_TOKEN=$(gh auth token) python -m lab04.collect_real_data
```

O CSV versionado é o registro congelado da amostra (coleta de 05/11/2026). Uma nova coleta
pode divergir, porque o quadro depende das estrelas atuais e PRs ou reviews podem ser
editados.

O CSV alimenta o gerador de #62:

```bash
python -m lab04.simulation --input lab04/data/real_prs.csv --seed 42
```

## Colunas de `real_prs.csv`

| Coluna | Conteúdo |
|---|---|
| `group`, `value` | Grupo e horas até o merge; são as colunas lidas por `lab04.simulation` |
| `repository`, `pr_number`, `source_url` | Identificação e link do PR |
| `created_at`, `merged_at` | Instantes em UTC usados no cálculo de `value` |
| `review_bots` | Bots da lista que revisaram antes do merge, separados por `;` |
| `additions`, `deletions`, `changed_files` | Tamanho do PR |
| `collected_at` | Instante em que a amostra foi gravada |
| `source`, `method`, `limitations` | Fonte, método e limitações, repetidos em cada linha |
