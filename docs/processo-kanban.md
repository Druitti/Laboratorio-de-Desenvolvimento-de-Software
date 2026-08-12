# Configuracao do processo — GitHub Projects

## Board

Colunas do campo **Status** (ordem do fluxo):

`Backlog` → `To Do` → `Doing` → `Review` → `Done`

- Cartões = **Issues** reais do repositorio (nao draft issues).
- Toda Issue de trabalho tem **Assignee**.
- Commits devem citar o numero da Issue (ex.: `#3 adiciona campos RQ01 e RQ02`).

## Limite de WIP (Doing)

**WIP maximo na coluna Doing: 2**

Justificativa: o grupo e um trio; limitar a 2 itens em paralelo reduz trabalho paralelo demais, forca fechar o ciclo `Doing → Review → Done` com mais frequencia e facilita a revisao semanal do professor. Mesmo com um unico integrante ativo, o limite permanece 2 para treinar a disciplina do fluxo.

## Labels de segregacao

| Label | Papel |
|---|---|
| `integrande-gabriel` | Integrante A |
| `Integrante-B` | Integrante B |
| `Integrante-C` | Integrante C |

## Lab01 — Issues

### S01 (esta semana)

| Issue | Titulo |
|---|---|
| #2 | Setup GitHub Projects + WIP + labels (Done) |
| #1 | Query GraphQL base + auth + fetch 100 repos |
| #3 | Metricas RQ01+RQ02 + validacao |
| #4 | Metricas RQ03+RQ04 + validacao |
| #5 | Metricas RQ05+RQ06 + ref TIOBE + validacao |
| #6 | Integracao script unico + smoke 100 repos |

### S02 / S03 / Relatorio (Backlog)

| Issue | Sprint |
|---|---|
| #7 | S02 — Paginacao 1000 + CSV |
| #8 | S02 — Snapshot GraphQL do Project |
| #9 | S02 — Hipoteses informais |
| #10 | S03 — Analise/visualizacao |
| #11 | Relatorio final + print do board |

## Snapshot de sprint

A partir da S02, o script `scripts/export_project_snapshot.py` exporta Status das Issues do Project para CSV (requer `gh auth refresh -s read:project,project`).
