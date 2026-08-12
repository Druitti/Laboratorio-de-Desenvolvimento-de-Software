# Laboratorio de Experimentacao de Software

Repositorio do grupo para a disciplina **Laboratorio de Experimentacao de Software** (PUC Minas).

## Lab01 — Caracteristicas de repositorios populares + Setup do Kanban

### Links

- Repositorio: https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software
- GitHub Projects (v2): *cole o URL do Project do grupo aqui* (ex.: `https://github.com/users/Druitti/projects/N`)
- Processo / WIP: [docs/processo-kanban.md](docs/processo-kanban.md)

### Divisao por integrante (trio)

| Papel | Label | RQs / foco S01 |
|---|---|---|
| A | `integrande-gabriel` | Setup (#2), query base (#1), RQ01+RQ02 (#3), integracao (#6) |
| B | `Integrante-B` | RQ03+RQ04 (#4); S02 paginacao (#7) |
| C | `Integrante-C` | RQ05+RQ06 (#5); S02 snapshot (#8) |

Enquanto o grupo estiver com uma pessoa, todas as Issues S01 ficam com Assignee `Druitti`.

### Fonte RQ05 (linguagens populares)

[TIOBE Index](https://www.tiobe.com/tiobe-index/) — referencia unica mantida em todo o Lab01.

### Como rodar (Lab01S01)

```bash
pip install -r requirements.txt
# Autenticacao: gh auth login  OU  defina GITHUB_TOKEN no ambiente / .env
python src/collect_repos.py          # top 100 repos + metricas RQ01-06
python src/validate_sample.py        # validacao rapida (amostra 5-10)
```

Saida local em `data/` (ignorada pelo git).

### Commits e Issues

Todo commit de trabalho referencia a Issue (`#N ...`). A correcao e feita a partir do board.
