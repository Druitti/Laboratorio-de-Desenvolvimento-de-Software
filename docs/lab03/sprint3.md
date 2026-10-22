# Sprint 3 — análises e reprodução

Implementação de #52, #53, #54 e #55 em `lab03/analysis.py`. A coleta e a
validação da S02 são pré-requisitos. Executar código com uma amostra parcial não
conclui a sprint. As issues permanecem abertas até a execução final comprovada.

## Execução

```bash
python -m pip install -r lab03/requirements.txt
python -m lab03.pipeline --config lab03/config.json --out lab03/data/s02 --workers 4
python -m lab03.validation prepare --help
python -m lab03.analysis --data lab03/data/s02 --gold lab03/data/gold --out lab03/results/final
```

A pasta de saída precisa ser nova. `--gold` recebe `manifest.json`, os CSVs
individuais `Druitti.csv`, `gabsant07.csv`, `Tavaresds1.csv` e
`consensus_review.csv`, gerados pelo fluxo da #45. O programa confere os hashes
das fontes, revalida os votos e decisões e recalcula Fleiss e precisão/recall/F1.
Não basta criar um arquivo afirmando que a heurística foi validada. F1 < 0,70
impede a entrega final; a versão precisa ser refinada e reavaliada.

Para diagnóstico explícito, sem declarar a entrega concluída:

```bash
python -m lab03.analysis --data lab03/data --out lab03/results/exploratory --exploratory
```

O modo exploratório aceita amostra menor que 300 e ausência de avaliação humana;
identifica essas limitações no manifesto e no relatório. Não preenche CFR(b) com
zeros. Nenhuma avaliação de um integrante é gerada como se fosse de outro.
Cada avaliação deve preservar os links examinados e as justificativas das
decisões. Concordância e consenso só serão calculados a partir de avaliações
independentes efetivamente disponíveis.

## Decisões estatísticas

- Unidade de análise: repositório. Janela fixa de 365 dias, UTC, fim exclusivo.
- RQ01–04: mediana, Q1, Q3, IQR, n válido e ausências. Frequência = releases / (365/7).
- CFR(a) mede falhas de CI, não incidentes de produção. Recuperação sem episódios
  observados é ausente; episódios censurados ficam no dataset.
- Classes: cortes da tabela do professor; mediana das quatro notas, arredondada
  para baixo. A referência de um mês para frequência é 365/12 dias. Qualquer
  métrica ausente impede a classificação geral; não se calcula mediana de três.
- RQ05: Spearman pareado, rho, p e n; séries constantes ou insuficientes não
  recebem correlação inventada. A dispersão usa frequência em escala log.
- RQ06: três fatores pré-especificados (estrelas, contribuidores, idade), quartis
  por valores, sem separar artificialmente empates. Cada fator é comparado com
  as seis variantes de métricas disponíveis. Kruskal–Wallis com epsilon²=H/(n−1)
  ou Mann–Whitney bilateral com delta de Cliff orientado do primeiro para o
  segundo grupo, em ordem crescente. Grupos com menos de duas observações não
  sustentam teste. Holm é aplicado a todos os testes válidos da mesma execução;
  quando CFR(b) chega, todos os ajustes são recalculados (até 18 testes).
- RQ07: C1=release/LT(a)/CFR(a); C2=release/LT(b)/CFR(a);
  C3=release+prerelease/LT(b)/CFR(a); C4=release/LT(b)/CFR(b).
  Recuperação é a mesma nas quatro. São combinações permitidas pelo enunciado;
  os exemplos com tags não são uma obrigação de usar exatamente aquela tabela.
  C2 isola a mudança de lead time; C3 acrescenta a definição de entrega;
  C4 isola CFR. As tags não são tratadas como releases datadas artificialmente.
- Sensibilidade usa os mesmos repositórios em cada par, informa perdas e kappa
  de Cohen linear na ordem Low, Medium, High, Elite. Uma única classe comum
  torna kappa indefinido, mesmo quando a proporção de mudanças é zero.
- As previsões corretivas `uncertain` não são descartadas da avaliação: são
  não positivas para precisão/recall/F1 da classe `yes`; contagem publicada.
  No CFR(b), referências com desfecho incerto são separadas do denominador,
  conforme a implementação da #49, e sua quantidade é explicitada.

## Artefatos

`dataset.csv` contém uma linha por elegível; `descriptive.csv`, `rq05.csv`,
`rq06.csv`, `rq06_groups.csv`, `classes.csv`, `rq07.csv` e `transitions.csv`
permitem inspecionar os números sem extrair dados dos gráficos. `manifest.json`
registra janela, hashes, fórmulas de agrupamento e impedimentos. Quando há
validação, `heuristic_validation.json` preserva o desempenho e Fleiss.

Figuras: distribuições acumuladas (sem esconder extremos), dispersão com
unidades, contagens por classe e matrizes de transição. `resultados.md` é texto
de apoio gerado a partir da mesma execução, com limites explícitos. A versão
final deverá ser incorporada ao artigo SBC; o diagnóstico parcial não é esse
artigo e não substitui a discussão dos resultados finais.

## Dicionário do dataset

Campos vazios significam ausências, nunca zero implícito. Frações estão em [0,1].

| Campos | Tipo / unidade | Origem e significado |
|---|---|---|
| repository, repository_id, default_branch | texto, inteiro, texto | Identidade GitHub e branch observada |
| stars, language | inteiro, texto | Metadados na coleta, não snapshot de 2025 |
| contributors, contributors_status | inteiro opcional, texto | Contribuidores e motivo de indisponibilidade |
| created_at, collected_at | ISO UTC | Criação e instante de coleta dos metadados |
| age_days_at_window_end | decimal / dias | Idade no fim da janela |
| workflows, selection_status | inteiro, texto | Metadados de workflows e elegibilidade comprovada |
| stable_releases, releases_with_pre | inteiro | Releases publicadas na janela e branch; segunda inclui pré-releases |
| valid_runs | inteiro | Runs push da branch, sucesso ou falha conforme enunciado |
| deployment_frequency, deployment_frequency_pre | decimal / semana | Contagem de releases / duração em semanas |
| lead_time_release_hours, lead_time_commit_hours | decimal / horas | Medianas por release e por inclusão de commit, série estável |
| lead_time_pre_commit_hours | decimal / horas | Mediana por commit na série com pré-releases |
| ignored_releases | inteiro | Intervalos estáveis sem lead time utilizável |
| cfr_ci | fração | Runs com falha / runs válidos |
| cfr_delivery, cfr_delivery_status | fração opcional, texto | CFR(b) e estado da validação humana |
| cfr_delivery_denominator | inteiro, quando validado | Releases de referência com acompanhamento completo e desfecho conhecido |
| cfr_delivery_censored | inteiro, quando validado | Releases sem sete dias completos de acompanhamento |
| cfr_delivery_uncertain | inteiro, quando validado | Referências cujo desfecho permanece incerto |
| recovery_hours | decimal / horas | Mediana dos episódios encerrados dentro da janela |
| recovery_episodes, recovery_censored | inteiros | Episódios totais e não encerrados |
| recovery_censored_ratio | fração opcional | Censurados / episódios; ausente quando não há episódios |

## Estado da retomada

A pasta `data/s02` foi iniciada a partir dos brutos locais de S01 e do checkpoint
`data/selection_expand_1/selection_state.json`, preservando janela e filtros.
Somente alvo e teto da busca foram ampliados, conforme config.json. O original
foi preservado. A migração fica registrada no checkpoint. A coleta antiga tinha
38 elegíveis; os resultados finais deverão registrar o novo funil e a amostra
congelada. O processo não presume que os primeiros 300 candidatos sejam elegíveis.

Na retomada, respostas de runs com menos IDs que `total_count` são subdivididas
em duas janelas, mesmo abaixo do teto de 1000. Ambas precisam ser completas;
os IDs da resposta truncada são descartados. A recuperação tem limite de oito
subdivisões por truncamento e respeita o intervalo mínimo de dois segundos.
Persistindo a divergência, o repositório continua pendente, nunca elegível por
aproximação. Mudanças de contagem entre páginas também invalidam a resposta
original e acionam subdivisão; somente as novas consultas completas são aceitas.
