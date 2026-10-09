# Lab03S01 — Tavares — issues #43 e #44

Responsável: Gabriel Tavares (`Tavaresds1`). Janela: `[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`.

## O que foi implementado

- `lab03/http.py`: transporte compartilhado (`CachedTransport`), mesmo contrato
  de `RestTransport` (`get(path, params=None) -> (payload_json, links)`), com
  cache em disco por requisição, espera automática de rate limit
  (`X-RateLimit-Remaining`/`X-RateLimit-Reset`) e backoff exponencial 1/2/4/8s
  para erros 5xx. Só grava em cache respostas bem-sucedidas; um erro nunca fica
  em cache e é repetido na próxima execução.
- `lab03/runs.py`: coleta de workflow runs do default branch, evento `push`,
  dentro da janela, dividida em meses e subdividida recursivamente sempre que
  uma sub-janela atinge 1000 resultados. Exporta `runs_evidence.json` (mesmo
  envelope de `releases_evidence.json`, com `valid_runs` no lugar de
  `stable_releases`) e `cfr_recovery.csv`.
- `lab03/metrics.py` (ampliado): `change_failure_rate` (CFR(a)) e
  `recovery_episodes` (tempo de recuperação por episódio, por workflow, com
  censura preservada), além do `lead_time` já existente de Santiago.
- `lab03/pipeline.py`: comando único da issue #44 — injeta o mesmo
  `CachedTransport` em `selection.collect`, `releases.collect` e
  `runs.collect`, roda `selection.finalize` e amplia `target_candidates`
  automaticamente (até o teto de uma busca única, 1000) enquanto faltarem
  elegíveis, falhando de forma explícita se não for possível.
- `lab03/tests/test_http.py`, `lab03/tests/test_runs.py`,
  `lab03/tests/test_pipeline.py`: fixtures offline, sem tocar a rede.
- `.github/workflows/lab03.yml`: passo de cobertura ampliado para
  `lab03.selection`/`lab03.releases`/`lab03.runs`/`lab03.http`, mais um passo
  dedicado exclusivamente a `lab03.metrics`.
- `.gitignore`: `lab03/data/cache/` (cache de requisições, regenerável).

Esta entrega não implementa CFR(b)/validação manual da S02 nem as análises
estatísticas da S03.

## Classificação de runs (seção 3 do enunciado)

| `conclusion` | Tratamento |
|---|---|
| `success` | Sucesso |
| `failure`, `timed_out`, `startup_failure` | Falha |
| `cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio | Ignorado |

CFR(a) = falhas ÷ (falhas + sucessos); sem nenhum dos dois, o valor é `None`,
nunca zero. `valid_runs` = falhas + sucessos únicos (por `id`) na janela.

## Episódios de recuperação

Um episódio começa na primeira falha **após um sucesso** do mesmo workflow
(falhas antes do primeiro sucesso observado não abrem episódio) e termina no
`updated_at` do próximo sucesso daquele workflow; falhas intermediárias e runs
ignorados não criam novos episódios nem interrompem o aberto. Um episódio sem
sucesso posterior na janela é **censurado**: preservado com duração `None`,
nunca descartado — `recovery_hours` é a mediana só dos episódios não
censurados, e `censored_ratio` informa a proporção de censura. Episódios nunca
misturam workflows diferentes.

## Executar no PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r lab03/requirements.txt
.\.venv\Scripts\python.exe -m pytest lab03/tests --cov=lab03 --cov-report=term-missing --cov-fail-under=80
```

Defina `GITHUB_TOKEN` no ambiente antes de qualquer coleta real:

```powershell
$tokenSeguro = Read-Host 'Token GitHub (não será exibido)' -AsSecureString
$env:GITHUB_TOKEN = [System.Net.NetworkCredential]::new('', $tokenSeguro).Password
```

Coleta isolada de runs (equivalente ao `releases.py` de Santiago):

```powershell
.\.venv\Scripts\python.exe -m lab03.runs --config lab03/config.json --candidates lab03/data/selection/candidates.csv --out lab03/data --limit 3
```

Pipeline único (issue #44), a partir da raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -m lab03.pipeline --config lab03/config.json
```

Reaproveita `lab03/data/selection` se a configuração já bater com o checkpoint
existente (não refaz a busca nem as chamadas já concluídas); só abre uma pasta
nova (`selection_expand_N`) quando precisa ampliar `target_candidates` além do
que já foi coletado. O comando retorna código 1 se não atingir o número de
elegíveis configurado.

## Arquivos gerados e dicionário

| Arquivo/campo | Tipo / unidade | Origem / significado |
|---|---|---|
| `runs_evidence.json` | JSON | Envelope compatível com o finalizador de Ferreira |
| `valid_runs` | inteiro ou null | Runs com `conclusion` em sucesso/falha, únicos por `id`, na janela |
| `raw/owner/repo/runs.json` | JSON | Runs classificados, `cfr` e `recovery` calculados sobre eles |
| `cfr_recovery.csv: cfr_ci` | proporção ou vazio | Falhas ÷ (falhas + sucessos) |
| `cfr_recovery.csv: recovery_hours` | horas ou vazio | Mediana dos episódios não censurados |
| `cfr_recovery.csv: recovery_censored_ratio` | proporção ou vazio | Episódios censurados ÷ total de episódios |
| `lab03/data/cache/*.json` | JSON | Cache por requisição do transporte compartilhado; não versionado |

## Limitações para relatar no artigo

CFR(a) mede falha de pipeline de CI, não falha de entrega em produção — uma
release pode ter sido publicada sem que todo workflow tenha rodado com
sucesso, e vice-versa; essa divergência é discutida na RQ03. A subdivisão de
janelas por `total_count` depende do teto documentado de 1000 resultados por
consulta da API de runs; repositórios com dezenas de workflows paralelos podem
gerar volumes altos mesmo em poucos dias. O cache em disco acelera retomadas,
mas também significa que uma resposta cacheada não reflete mudanças no
GitHub após a primeira coleta — uma atualização de dados exige uma pasta de
cache nova. A espera de rate limit e o backoff podem alongar bastante a
duração de uma coleta completa.

## Verificação local

```powershell
.\.venv\Scripts\python.exe -m pytest lab03/tests --cov=lab03 --cov-report=term-missing --cov-fail-under=80
```
