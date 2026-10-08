# Lab03S01 — Santiago — issue #42

Responsável: Gabriel Santiago (`gabsant07`). Janela: `[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`.

## O que foi implementado

- `lab03/releases.py`: coleta REST própria, releases e pré-releases, tags com data do commit, ancestralidade no default branch, comparação paginada e exportação.
- `lab03/metrics.py`: lead time em horas, por release e por inclusão de commit.
- `lab03/tests/test_releases.py`: fixtures offline e casos de borda, inclusive comparação com 301 commits em quatro páginas.
- `lab03/selection.py`: pequena alteração no leitor de evidência para aceitar `null` apenas em contagem incompleta; as evidências completas continuam exigindo inteiro não negativo.
- `.github/workflows/lab03.yml`: testes de seleção, releases e métricas; checagem adicional de cobertura exclusiva das métricas.

Os projetos 1 e 2 foram preservados. Esta entrega implementa a issue #42 da S01. Não implementa CFR(b)/validação manual da S02 nem as análises estatísticas da S03.

## Executar no PowerShell

Abra no VS Code a pasta que contém `lab03`, `docs` e `.github`. Execute a partir dessa raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r lab03/requirements.txt
.\.venv\Scripts\python.exe -m pytest lab03/tests --cov=lab03.selection --cov=lab03.releases --cov=lab03.metrics --cov-report=term-missing --cov-fail-under=80
```

Não precisa ativar o ambiente virtual nem mudar a política de execução do PowerShell.
Defina `GITHUB_TOKEN` no ambiente antes da coleta. Para não colocar o token em um comando do histórico:

```powershell
$tokenSeguro = Read-Host 'Token GitHub (não será exibido)' -AsSecureString
$env:GITHUB_TOKEN = [System.Net.NetworkCredential]::new('', $tokenSeguro).Password
```

Primeiro, uma execução pequena em pasta própria, para não misturar a coleta com a execução completa:

```powershell
.\.venv\Scripts\python.exe -m lab03.releases --config lab03/config.json --candidates lab03/data/selection/candidates.csv --out lab03/data/teste-santiago --limit 3
```

Depois, a lista completa dos candidatos já fornecida por Ferreira:

```powershell
.\.venv\Scripts\python.exe -m lab03.releases --config lab03/config.json --candidates lab03/data/selection/candidates.csv --out lab03/data
```

Uma coleta completa usa checkpoint por repositório. Rodar novamente na mesma pasta reutiliza os repositórios completos e repete os incompletos. Para atualizar dados ou mudar janela/branch, escolha outra pasta com `--out`.
O programa retorna código 1 quando há repositórios pendentes; inspecione `releases_evidence.json` e os brutos. Não ignore esse retorno.
O transporte mínimo disponível no projeto interrompe chamadas com erro de API; não faz espera automática. A camada compartilhada de cache/rate limit ainda deve ser fornecida pela issue #43.

## Integração com Tavares (#43/#44)

A função pública tem a assinatura:

```python
from lab03.releases import collect

# client é o mesmo transporte com cache/rate limit usado na seleção e nos runs.
# candidates é uma lista de dicionários de candidates.csv.
evidence = collect(client, config, candidates, out)
```

O cliente precisa fornecer `get(path, params=None) -> (payload_json, links)`.
Os paths são relativos à API REST e `links` usa o formato de `requests.Response.links`.
O coletor não instancia cliente HTTP quando chamado por essa função. Assim, todas as chamadas passam pelo cache, rate limit e backoff do cliente recebido.

Também existe `--transport modulo:factory`: a função `factory()` do módulo indicado retorna o cliente compartilhado configurado. Exemplo apenas de interface, a adaptar ao nome real do módulo de #43:

```powershell
.\.venv\Scripts\python.exe -m lab03.releases --transport lab03.http:build_client
```

Esse módulo não existe neste ZIP: é o ponto de integração, não um comando já executável.
Com `runs_evidence.json` produzido por #43, o finalizador existente pode ser chamado:

```powershell
.\.venv\Scripts\python.exe -m lab03.selection finalize --state lab03/data/selection/selection_state.json --releases lab03/data/releases_evidence.json --runs lab03/data/runs_evidence.json
```

A integração no comando único é de #44. Este componente fornece a função chamável e a evidência que esse comando consome. Os 100 candidatos existentes não comprovam 100 elegíveis. Se os filtros de 5 releases e 50 runs deixarem menos de 100, Ferreira deve ampliar candidatos e o pipeline deve coletar os novos repositórios.

## Regras de coleta e decisões

1. Releases são paginadas até terminar `Link.next`; IDs duplicados são removidos. Drafts ficam no bruto, sem entrar no cálculo. `published_at` define a janela, com fim exclusivo. Releases posteriores à janela ficam marcadas, sem comparação.
2. `GET /commits/{branch}` fixa o SHA do HEAD atual. `GET /commits/{tag}` resolve a tag em commit, incluindo tags anotadas e leves. `target_commitish` é preservado no bruto, mas não é prova de branch.
3. `compare/{commit_da_tag}...{HEAD}` com status `ahead` ou `identical` comprova ancestralidade. `behind` e `diverged` não comprovam inclusão. Essa consulta de prova não precisa enumerar commits; a paginação completa é aplicada às comparações que alimentam o lead time.
4. A série principal contém somente releases estáveis comprovadas no branch. Ordena por `published_at`, com ID como desempate. Mantém o histórico anterior à janela para localizar o predecessor imediato; a release de contexto não soma ao limiar de inclusão. A primeira release sem predecessor fica com `no_previous_release`.
5. A série alternativa inclui pré-releases e possui seus próprios predecessores. Tags ficam registradas com SHA e `commit.author.date`, indicador de janela e prova de ancestralidade. As variantes são preservadas para RQ07; não há classificação DORA ou análise de sensibilidade nesta entrega.
6. Comparações entre releases usam SHA fixado, `per_page=100` e todos os `Link.next`. São deduplicadas por SHA dentro do intervalo e verificadas contra `total_commits`. Mudança de contagem/status ou truncamento interrompe a coleta e deixa evidência incompleta.
7. `compare` 404 fica com `compare_404`: ignora somente aquele intervalo de lead time e mantém a contagem de releases comprovadas. Outro erro de API deixa o repositório incompleto. Tag de release não resolvida com 404 impossibilita confirmar contagem/branch: `complete=false`, contagem `null`, nunca zero. Tags alternativas não resolvidas também deixam a coleta pendente.
8. Intervalo sem commits: `no_commits`, sem valor numérico. Histórico que não avança (`behind`/`diverged`): `non_forward_history`, sem lead time. Data ausente, inválida, sem timezone ou posterior à publicação invalida o intervalo inteiro como `inconsistent_dates`. Esses casos são contabilizados como ignorados. Lead time zero é válido somente quando a data do commit coincide com a publicação.
9. Por release: maior diferença entre publicação e datas de autoria do intervalo; agregado pela mediana entre releases válidas. Por commit: mediana das diferenças de todos os intervalos válidos, com o peso de cada inclusão. SHA repetido em releases distintas é mantido como inclusão distinta. Valores ausentes são `null` no JSON e células vazias no CSV.

## Arquivos gerados e dicionário

| Arquivo/campo | Tipo / unidade | Origem / significado |
|---|---|---|
| `releases_evidence.json` | JSON | Envelope compatível com o finalizador de Ferreira |
| `window_start`, `window_end` | timestamp UTC | Configuração da coleta; início inclusivo, fim exclusivo |
| `repository`, `default_branch` | texto | Dados de candidates.csv |
| `complete` | booleano | Todas as listagens/provas concluídas; false não significa zero releases |
| `stable_releases` | inteiro ou null | Releases não draft, não prerelease, na janela e ancestrais do HEAD fixado |
| `evidence_path` | caminho | Bruto auditável produzido na execução |
| `error_type` | texto ou null | Classe do erro que interrompeu a coleta; sem credenciais/mensagem do transporte |
| `raw/owner/repo/releases.json` | JSON | Releases originais, tags, SHA do HEAD, provas, comparações e auditoria dos cálculos |
| `comparisons.stable` | lista | Comparações da definição principal, com base/head e commits originais |
| `comparisons.with_prereleases` | lista | Comparações da definição alternativa |
| `metrics.*.intervals` | lista | Situação e lead time de cada intervalo, inclusive os ignorados |
| `lead_time.csv: lead_time_release_hours` | horas ou vazio | Mediana dos máximos por release |
| `lead_time.csv: lead_time_commit_hours` | horas ou vazio | Mediana de todas as inclusões de commits |
| `measured_releases` | inteiro ou vazio | Número de intervalos válidos usados |
| `measured_commit_inclusions` | inteiro ou vazio | Número de inclusões de commits válidas |
| `ignored_releases` | inteiro ou vazio | Intervalos sem predecessor, 404, sem commits, história não progressiva ou datas inválidas |

## Verificação local

Execução offline em Python 3.12: **55 testes passaram** (25 novos de Santiago e 30 existentes de Ferreira). Cobertura: `lab03.metrics` **100%**, `lab03.releases` **97%**, `lab03.selection` **91%**, total **95%**. A checagem exclusiva de `lab03.metrics` também passou com 100%.

Os testes cobrem o exemplo de 13/5/1 dias do enunciado, diferença de ponderação das medianas, releases sem predecessor, datas inválidas/negativas, commits duplicados, 301 commits paginados, links inválidos/cíclicos, truncamento, 404, branches divergentes, fim exclusivo da janela, pré-releases, tags, exportação, retomada, erros de API e contrato de evidência.

Não foi executada coleta autenticada no GitHub nesta entrega; não foram gerados dados reais de releases/lead time nem comprovação de 100 elegíveis. O CI está configurado, mas precisa ser executado pelo GitHub após o commit. O artefato bruto da fixture, quando usado em testes, é apenas dado sintético e não pode ser apresentado como resultado empírico.

## Limitações para relatar no artigo

A ancestralidade é observada no HEAD atual, não no branch histórico de 2025. Tags apagadas/recriadas, force-push, releases em branches de manutenção e branches padrão renomeados podem mudar a seleção. Rebase/squash pode distorcer `commit.author.date`. Releases são proxies de deploy, e um commit antigo pesa mais na variante por release. Comparações com erro/datas inconsistentes são perdas de medição, não censura de recuperação de CI. Os contadores de exclusão devem acompanhar a análise futura.

## Commit e entrega no GitHub

Depois de copiar e testar os arquivos no checkout do grupo, confira `git diff` e faça um commit referenciando a issue:

```powershell
git add lab03/releases.py lab03/metrics.py lab03/tests/test_releases.py lab03/selection.py lab03/README.md docs/lab03/santiago-s01.md docs/lab03/contrato-integracao.md .github/workflows/lab03.yml
git commit -m "feat(lab03): coleta releases e lead time de Santiago #42"
```

Mantenha a issue aberta até juntar a coleta real, o link da execução de CI e a evidência da integração de #44. Nenhum commit, push ou alteração de Issue foi realizado por esta entrega.

## Referências de implementação

- [API REST de commits e compare](https://docs.github.com/en/rest/commits/commits)
- [Releases](https://docs.github.com/en/rest/releases/releases)
- [Tags de repositório](https://docs.github.com/en/rest/repos/repos#list-repository-tags)
- [Paginação REST](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)

## Logs de progresso

A coleta agora imprime horário, repositório atual e posição na lista, etapa,
páginas recebidas, releases e tags em processamento, comparações e resultado
dos cálculos. Ao terminar cada repositório, imprime duração, situação e gravação
das evidências. Checkpoints reutilizados aparecem explicitamente.

Para detalhes adicionais de resolução de commits e ancestralidade, use:

```powershell
.\.venv\Scripts\python.exe -m lab03.releases --out lab03/data/teste-logs --limit 3 --verbose
```

A pasta nova permite observar uma coleta nova. Usar a mesma pasta da execução
anterior reutiliza os checkpoints completos. Para acompanhar todos os candidatos,
remova `--limit 3` e escolha a pasta de saída desejada.

Os logs são emitidos em tempo real no terminal. Erros mostram a classe e o código
HTTP quando disponível; o texto bruto da exceção e as credenciais não são impressos.
O pipeline integrador pode configurar `logging` e usar o logger `lab03.releases`.
