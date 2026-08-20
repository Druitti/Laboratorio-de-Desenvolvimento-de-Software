# Hipóteses informais — Lab01 (Issue #9)

Primeira versão das hipóteses informais sobre as questões de pesquisa, organizadas pelos três blocos do trio. Estas hipóteses serão confrontadas com os dados dos 1.000 repositórios nas sprints seguintes (análise S03 e relatório final).

**Fonte de “linguagens mais populares” (RQ05/RQ07):** [TIOBE Index](https://www.tiobe.com/tiobe-index/) — referência mantida em todo o Lab01.

---

## Bloco A — RQ01 e RQ02 (`integrande-gabriel`)

### RQ01 — Sistemas populares são maduros/antigos?

**Hipótese informal:** Sim. Esperamos que a mediana da idade dos repositórios mais estrelados seja elevada (da ordem de vários anos), porque popularidade no GitHub tende a acumular-se com o tempo: projetos jovens raramente entram no topo absoluto de estrelas.

**Métrica:** idade do repositório a partir de `createdAt`.

### RQ02 — Sistemas populares recebem muita contribuição externa?

**Hipótese informal:** Em parte. Esperamos um total mediano de pull requests *merged* relativamente alto, porém com forte assimetria: poucos repositórios (ex.: frameworks e plataformas grandes) concentram milhares de PRs, enquanto listas “awesome” e repositórios de conteúdo podem ter poucas PRs aceitas apesar das estrelas.

**Métrica:** `pullRequests(states: MERGED).totalCount`.

---

## Bloco B — RQ03 e RQ04 (`Integrante-B`)

### RQ03 — Sistemas populares lançam releases com frequência?

**Hipótese informal:** Não necessariamente. Esperamos mediana de releases baixa ou próxima de zero no conjunto dos mais populares, porque muitos repositórios de alto sucesso são curadoria/documentação (sem tags de release) ou monorepos que versionam de outras formas. Projetos de software “clássicos” (bibliotecas, runtimes) devem puxar a cauda superior da distribuição.

**Métrica:** `releases.totalCount`.

### RQ04 — Sistemas populares são atualizados com frequência?

**Hipótese informal:** Sim, em geral. Esperamos que o tempo desde o último `pushedAt` seja curto para a maioria (mediana da ordem de dias ou poucas semanas): manter relevância e estrela alta costuma exigir atividade recente, ainda que existam outliers “congelados” porém históricos.

**Métrica:** tempo desde `pushedAt` (e/ou `updatedAt` como apoio).

---

## Bloco C — RQ05, RQ06 e bônus RQ07 (`Integrante-C`)

### RQ05 — Sistemas populares são escritos nas linguagens mais populares?

**Hipótese informal:** Parcialmente. Esperamos que uma fração relevante use linguagens do topo TIOBE (ex.: Python, JavaScript/TypeScript, Java, C/C++, Go), mas também uma parcela não desprezível em Markdown/`null` (listas e docs) ou em linguagens fora do ranking TIOBE (ex.: TypeScript, se não estiver na lista de referência adotada). Ou seja: correlação positiva com TIOBE, sem monopólio.

**Métrica:** `primaryLanguage.name`, classificada contra o TIOBE Index.

### RQ06 — Sistemas populares possuem alto percentual de issues fechadas?

**Hipótese informal:** Sim. Esperamos razão mediana *issues fechadas / total de issues* alta (acima de ~70–80%), refletindo comunidades ativas que triagem e fecham issues; valores ausentes ou razão indefinida podem ocorrer quando o total de issues é zero.

**Métrica:** `closedIssues.totalCount / issues.totalCount`.

### RQ07 (bônus) — Linguagens mais populares implicam mais PRs, releases e atualizações?

**Hipótese informal:** Mista. Esperamos que repositórios cuja linguagem primária está no TIOBE tenham, em mediana, mais PRs merged e atualizações mais recentes do que o grupo “fora do TIOBE”; para releases, a diferença deve ser menor ou nula, porque o efeito “repo de conteúdo sem release” atravessa ambos os grupos.

**Métrica:** cruzamento das métricas das RQ02, RQ03 e RQ04 por grupo TIOBE vs. não-TIOBE (e/ou por linguagem).

---

## Próximos passos

1. Confrontar cada hipótese com medianas/distribuições nos 1.000 repositórios (após Issue #7).
2. Incorporar este texto na introdução do relatório final (Issue #11).
