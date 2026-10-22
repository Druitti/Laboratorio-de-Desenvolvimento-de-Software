# Lab03 — coleta e análise

[Sprint 3: execução, decisões estatísticas e dicionário do dataset](../docs/lab03/sprint3.md).
O comando `python -m lab03.analysis` implementa RQ01–07. Exige coleta completa
e validação da S02 para entrega final; `--exploratory` identifica saídas parciais.

## Lab03S01 — pipeline único (#44)

Issue #44. Integra seleção (#41), releases/lead time (#42) e runs/CFR(a)/recuperação
(#43) com um único transporte compartilhado, cache em disco e rate limit/backoff.
Veja o [guia de execução, integração e evidência de Tavares](../docs/lab03/tavares-s01.md).

```bash
python -m pip install -r lab03/requirements.txt
# Defina GITHUB_TOKEN no ambiente sem salvar a credencial no repositório.
python -m lab03.pipeline --config lab03/config.json
```

Roda a seleção (reaproveitando `data/selection` se já existir), coleta releases e
runs para os candidatos pendentes, finaliza o funil e amplia a seleção
automaticamente até comprovar `target_candidates` elegíveis — ou falha de forma
explícita se a busca se esgotar antes disso. Saída em `data/final_selection/`.

# Lab03S01 — seleção e releases

A parte de Santiago, issue #42, está implementada em `releases.py` e `metrics.py`.
Veja o [guia de execução, integração e evidência de Santiago](../docs/lab03/santiago-s01.md).

# Lab03S01 — workflow runs, cache e métricas de CI (#43)

Issue #43. Transporte compartilhado com cache/rate limit/backoff (`http.py`),
coleta de workflow runs, CFR(a) e tempo de recuperação (`runs.py`, `metrics.py`).
Veja o [guia de execução, integração e evidência de Tavares](../docs/lab03/tavares-s01.md).

# Lab03S01 — seleção de Ferreira

[Complementação e correções da integração S01](../docs/lab03/complementacao-s01.md).

**S02:** [amostra-ouro, concordância e protocolo de rotulação](../docs/lab03/ferreira-s02.md)
e [texto-base de metodologia](../relatorio/lab03/metodologia.md).

Issue #41. Implementação da parte de Ferreira; coletores de Santiago (#42) e
Tavares (#43) são entregas separadas.

[Evidência da execução e resultados da validação](../docs/lab03/evidencia-s01.md).

```bash
python -m pip install -r lab03/requirements.txt
# Defina GITHUB_TOKEN no ambiente sem salvar a credencial no repositório.
python -m lab03.selection collect --config lab03/config.json
python -m pytest lab03/tests --cov=lab03.selection --cov-report=term-missing --cov-fail-under=80
```

Configuração: ano de 2025, UTC, fim exclusivo em 01/01/2026. Para a S02,
`target_candidates=300` (elegíveis exigidos) e `max_search_results=20000` (teto
configurado de repositórios examinados). Usa `stars:>1000`, `fork:false`,
`archived:false` e criação anterior ao fim da janela. Excluir forks e arquivados
é decisão de amostragem do grupo, não requisito do professor. A busca é um
recorte por popularidade, **não** amostragem aleatória nem enumeração de todos
os repositórios.

O teto de 1000 resultados é por **consulta**, não pela amostra inteira: em
`selection.search_candidates`, uma faixa de estrelas que estoura 1000
resultados é dividida automaticamente — a parte já obtida (`stars > limite`) é
aproveitada e o restante (`stars` entre o piso da faixa e o limite, incluindo
possíveis empates no corte) é buscado de novo como uma faixa menor. Isso se
repete recursivamente até cobrir toda a faixa `stars > min_stars` ou atingir
`max_search_results`. Se uma faixa de um único valor de estrelas ainda assim
tiver mais de 1000 repositórios (nunca observado na prática acima de
`min_stars=1000`), o comando falha explicitamente em vez de descartar
repositórios silenciosamente.

## Saídas

- `data/selection/metadata.csv`: todos os repositórios examinados e motivos.
- `data/selection/candidates.csv`: candidatos com Actions, ainda não elegíveis.
- `data/selection/funnel.csv`: contagens de etapas, exclusões e pendências.
- `data/selection/selection_state.json`: checkpoint dos metadados concluídos e configuração.

Interrupções preservam os repositórios concluídos. Rodar novamente repete a busca
para localizar os restantes, mas pula as chamadas de metadados dos já registrados.
Uma coleta concluída não faz chamadas ao retomar. Não alterar a configuração na
mesma pasta; use `--out` para uma coleta nova. Em HTTP 403/429/5xx, corrigir acesso
ou aguardar e retomar; a espera automática e o cache por resposta serão de #43.

Candidatos com Actions não significam repositórios elegíveis. A coleta histórica deve
comprovar ≥5 releases principais e ≥50 runs válidos na janela. O finalizador e os
formatos para os colegas estão em [contrato de integração](../docs/lab03/contrato-integracao.md).

## Dicionário da seleção

| Coluna | Tipo / unidade | Origem |
|---|---|---|
| repository | texto owner/repo | full_name |
| repository_id | inteiro | id estável da API |
| default_branch | texto | default_branch atual |
| stars | inteiro | stargazers_count no momento da coleta |
| language | texto ou vazio | language atual, vazio quando null |
| contributors | inteiro ou vazio | contributors?per_page=1&anon=true; última página do Link, ou tamanho da resposta sem paginação |
| contributors_status | categoria | measured, not_collected ou unavailable_large_history |
| created_at | timestamp UTC | created_at |
| age_days_at_window_end | dias decimais | (fim exclusivo da janela − created_at)/86400 |
| workflows | inteiro ou vazio | actions/workflows.total_count atual |
| collected_at | timestamp UTC | instante da obtenção dos metadados |
| selection_status | categoria | excluded_metadata, excluded_no_actions, pending_collectors; após integração também excluded_releases, excluded_runs, eligible |

Campos não consultados ficam vazios, não zero. O número de contribuidores é o total
exposto pelo endpoint, incluindo anônimos, e não uma contagem limitada a 2025.
Estrelas, linguagem, branch e presença de Actions são atuais; não representam um
snapshot retrospectivo de 2025. O endpoint de contribuidores possui cache próprio
e pode atrasar em relação ao Git. Isso deve ser descrito nas ameaças à validade.
Em históricos muito grandes, a API recusa listar contribuidores; essa limitação
específica é registrada como `unavailable_large_history`, com contagem vazia.
Ela não equivale a zero contribuidores nem exclui o repositório da seleção.

## Referências técnicas

- [Busca e teto de 1000 resultados](https://docs.github.com/en/rest/search/search#search-repositories)
- [Paginação Link](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
- [Metadados e contribuidores](https://docs.github.com/en/rest/repos/repos#list-repository-contributors)

Os testes usam fixtures pequenas, falhas de rede simuladas, limites de inclusão,
duplicação, paginação, retomada, incompatibilidade de janela e branch. O CI de
`.github/workflows/lab03.yml` exige 80% de cobertura de `lab03.selection`,
`lab03.releases`, `lab03.runs` e `lab03.http` em um passo, e 80% de
`lab03.metrics` isoladamente em outro — a cobertura de métricas é checada à
parte porque sustenta diretamente o cálculo de CFR(a), recuperação e lead time.
