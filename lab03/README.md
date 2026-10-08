# Lab03S01 — seleção de Ferreira

Issue #41. Implementação da parte de Ferreira; coletores de Santiago (#42) e
Tavares (#43) são entregas separadas.

```bash
python -m pip install -r lab03/requirements.txt
# Defina GITHUB_TOKEN no ambiente sem salvar a credencial no repositório.
python -m lab03.selection collect --config lab03/config.json
python -m pytest lab03/tests --cov=lab03.selection --cov-report=term-missing --cov-fail-under=80
```

Configuração: ano de 2025, UTC, fim exclusivo em 01/01/2026. A busca examina até
1000 resultados por popularidade para obter 100 candidatos com Actions. Usa
`stars:>1000`, `fork:false`, `archived:false` e criação anterior ao fim da janela.
Excluir forks e arquivados é decisão de amostragem do grupo, não requisito do
professor. A busca é um recorte por popularidade, **não** amostragem aleatória nem
enumeração de todos os repositórios. Fatiar a busca será necessário se o universo
de até 1000 não produzir candidatos suficientes após os filtros históricos.

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

100 candidatos não significam 100 repositórios elegíveis. A coleta histórica deve
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

## Referências técnicas

- [Busca e teto de 1000 resultados](https://docs.github.com/en/rest/search/search#search-repositories)
- [Paginação Link](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
- [Metadados e contribuidores](https://docs.github.com/en/rest/repos/repos#list-repository-contributors)

Os testes usam fixtures pequenas, falhas de rede simuladas, limites de inclusão,
duplicação, paginação, retomada, incompatibilidade de janela e branch. O CI de
`.github/workflows/lab03.yml` exige 80% de cobertura do seletor; isso **não substitui**
a cobertura do módulo de métricas exigida na integração de #42/#43.
