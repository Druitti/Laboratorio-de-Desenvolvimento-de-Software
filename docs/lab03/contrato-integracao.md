# Contrato de integração da seleção

Entrada comum: `lab03/config.json`. A janela usa UTC, início inclusivo e fim
exclusivo. Repositórios entram com seu nome completo e default branch registrados
em `lab03/data/selection/candidates.csv`.

## Evidência de releases — issue #42

```json
{
  "window_start": "2025-01-01T00:00:00Z",
  "window_end": "2026-01-01T00:00:00Z",
  "repositories": [{
    "repository": "owner/repo",
    "default_branch": "main",
    "complete": true,
    "stable_releases": 5,
    "evidence_path": "lab03/data/raw/owner_repo/releases.json"
  }]
}
```

O número é a contagem de releases principais, não draft, não prerelease, relacionadas
ao default branch e publicadas na janela. Não usar simplesmente `target_commitish`
como prova de ancestralidade: ele pode ser um SHA. O coletor deve documentar como
resolve tags e verifica sua relação com o branch. `complete` só é verdadeiro após
paginação e filtros completos. A release anterior fora da janela é contexto para
lead time, não soma à contagem de inclusão.

## Evidência de runs — issue #43

Mesmo envelope, substituindo `stable_releases` por `valid_runs` e indicando o
artefato bruto de runs em `evidence_path`. Contar IDs únicos, do default branch,
evento `push`, criados na janela, com conclusão `success`, `failure`, `timed_out`
ou `startup_failure`. As outras conclusões são ignoradas. Consultas limitadas a
1000 itens não são completas: subdividir a janela até garantir cobertura.

Os exemplos são apenas esquemas, **não são dados coletados**. Evidências com erro
de API ou paginação pendente usam `complete: false`; não substituir por zero.
Cada envelope deve ter no máximo uma linha por repositório.

## Finalizador de Ferreira

```bash
python -m lab03.selection finalize \
  --state lab03/data/selection/selection_state.json \
  --releases lab03/data/releases_evidence.json \
  --runs lab03/data/runs_evidence.json
```

Rejeita janelas, branches e contagens inconsistentes. As duas evidências completas
são necessárias para aprovar ou descartar pelos limiares; dados ausentes permanecem
pendentes. A referência ao bruto é obrigatória, mas o finalizador confia na contagem
produzida pelo coletor: não refaz a mineração nem certifica o conteúdo do artefato.
O funil usa motivos exclusivos: metadados → sem Actions → releases insuficientes
→ runs insuficientes → elegível; pendências são uma categoria separada.

## Transporte compartilhado

`selection.collect(client, config, out)` aceita qualquer objeto com
`get(path, params=None) -> (payload_json, links)`, onde `links` segue a forma de
`requests.Response.links`. O transporte básico só faz leituras REST de metadados,
interrompendo em erros; o checkpoint guarda metadados concluídos por repositório.
O cache de todas as respostas, espera por rate limit e backoff do pipeline completo
são de #43. A integração deve injetar esse transporte no seletor.

## Implementação de Santiago (#42)

`lab03.releases.collect(client, config, candidates, out)` exporta
`out/releases_evidence.json`, `out/lead_time.csv` e os brutos em
`out/raw/owner/repo/releases.json`. O cliente é injetado e segue o contrato
`get(path, params=None) -> (payload_json, links)` definido acima.

**Contagem desconhecida:** evidência incompleta pode usar `stable_releases: null`
(e igualmente `valid_runs: null`). Isso representa ausência de medição, não zero.
O leitor do finalizador aceita null somente com `complete: false`; um envelope
completo continua exigindo inteiro não negativo. Evidências incompletas preservam
a categoria pendente.

O HEAD do branch é fixado por SHA; uma release pertence ao branch quando
`compare/{release_sha}...{branch_sha}` retorna `ahead` ou `identical`.
Comparações entre releases são inteiramente paginadas e verificadas contra
`total_commits`. O [guia de Santiago](santiago-s01.md) documenta filtros,
ausências, variantes, dicionário de dados e limitações.
