# Complementação da S01 — #42, #43 e #44

Em 15/10/2026, após atualizar a `main`, a revisão identificou que os coletores
estavam implementados, mas não havia evidência versionada de 100 repositórios
elegíveis. A #44 foi reaberta: aprovação dos testes não substitui a coleta real.
Esta complementação foi autorizada por Ferreira, incluindo as pendências dos
componentes dos colegas; os commits mantêm referências às respectivas issues.

## Correções

- Transporte: retentativa de timeout/conexão com backoff limitado e tratamento
  de limite secundário/`Retry-After`, sem persistir falhas como dados válidos.
- Paginação: preservação dos filtros entre páginas e verificação de IDs únicos
  contra `total_count` de runs. Resultado truncado permanece pendente.
- Divisão de runs: subdivisão ao atingir 1000, inclusive exatamente 1000;
  cortes em segundos inteiros evitam perder eventos nas fronteiras.
- Validação local de branch, evento e data dos runs, além dos filtros da API.
  Checkpoints antigos de runs são reprocessados pelo coletor versão 2.
- Recuperação: sucesso que termina no fim exclusivo da janela ou depois dela
  não encerra o episódio dentro do período; a censura permanece registrada.
- Retomada: exportações parciais preservam linhas anteriores ainda não revisitadas,
  em vez de reduzir o CSV/JSON aos primeiros repositórios da nova execução.
- Releases: somente a antecessora necessária de cada série é resolvida antes
  da janela; tags fora da janela preservam data e SHA, sem comparação desnecessária
  de ancestralidade. O contexto e as variantes dentro da janela são preservados.
- Datas dos commits de tags são consultadas por GraphQL próprio, em lotes de até
  100 SHAs, usando `authoredDate` (data de autoria). O mesmo transporte aplica
  cache e limites; erros GraphQL não são gravados como resultados válidos.
  Sem esse recurso no transporte injetado, o coletor continua funcionando via REST.
- Releases são paginadas por GraphQL quando o transporte permite, preservando ID,
  tag, data, notas, flags e commit da tag, sem os metadados dos binários anexados.
  Esses anexos não são usados nas métricas. Os limites e as respostas continuam
  auditáveis pelo cache local.
- Nos artefatos versionados, runs preservam identificação, workflow, branch,
  evento, conclusão, datas e links; commits preservam SHA, autoria, mensagem,
  committer e link. Objetos redundantes de usuário/repositório não são repetidos
  em cada linha. As respostas integrais continuam no cache local, não versionado.

## Pré-filtro auditável

`lab03.screening` é integrado ao comando `python -m lab03.pipeline`. Ele evita
coletar todas as tags, comparações e runs de repositórios que já não podem atingir
os mínimos. A contagem de releases publicadas estáveis na janela, antes da prova
de branch, é um **limite superior** da contagem elegível. O `total_count` de runs
`push` na branch padrão também é um limite superior, pois inclui conclusões
ignoradas. Quando esses limites ficam abaixo de 5/50, a exclusão já está provada.

Passar pelo pré-filtro não comprova elegibilidade: ambos os coletores completos
continuam obrigatórios. Falhas HTTP permanecem pendentes, nunca viram zero.
`screening/screening.json` guarda contagens observadas e motivo; a seleção original
não é alterada. `screening/selection_state.json` aplica essas exclusões ao funil.
Somente as evidências completas dos coletores podem produzir `eligible`.
Após as retentativas de um lote, o pipeline pode ampliar a busca mesmo havendo
pendências; elas permanecem no funil e não entram na amostra elegível.

## Execução e conclusão

O comando e a janela continuam os mesmos: `python -m lab03.pipeline --config
lab03/config.json`, cobrindo `[2025-01-01, 2026-01-01)`, UTC. Cache e checkpoints
permitem continuar após interrupções sem repetir respostas já salvas. A execução
deve terminar com pelo menos 100 linhas elegíveis em
`lab03/data/final_selection/eligible.csv` para encerrar #44.

Na S02 o requisito passa a pelo menos 300 elegíveis (#50); terminar a S01 não
libera automaticamente o sorteio de 60 da amostra final. A rotulação continua
sendo avaliação humana independente, seguida de discussão dos três.

Os testes de regressão em `lab03/tests/test_completion.py` verificam as falhas
de rede, limites secundários, truncamento, fronteiras temporais, censura,
pré-filtro e preservação das exportações na retomada. Fixtures não são dados reais.
