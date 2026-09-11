# Laboratorio de Experimentacao de Software

Repositorio do grupo para a disciplina **Laboratorio de Experimentacao de Software** (PUC Minas).

## Lab01 — Caracteristicas de repositorios populares + Setup do Kanban

### Links

- Repositorio: https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software
- GitHub Projects (v2) (https://github.com/users/Druitti/projects/5)
- Processo / WIP: [docs/processo-kanban.md](docs/processo-kanban.md)

### Divisao por integrante (trio)

| Papel | Label | RQs / foco S01 |
|---|---|---|
| A | `integrande-gabriel` | Setup (#2), query base (#1), RQ01+RQ02 (#3), integracao (#6) |
| B | `Integrante-gabriel santiago` | RQ03+RQ04 (#4); S02 paginacao (#7) |
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

## Lab02 — Assistentes de IA vs. codificacao manual

- Divisao do trio: [docs/lab02/divisao-lab02.md](docs/lab02/divisao-lab02.md)
- Desenho do experimento: [docs/lab02/desenho-experimento.md](docs/lab02/desenho-experimento.md)
- Ambiente (Python, pytest, Radon, assistente de IA): [docs/lab02/ambiente.md](docs/lab02/ambiente.md)
- Katas: [lab02/katas/README.md](lab02/katas/README.md)

### Lab02S01 — Issues

| Issue | Responsavel | Entrega |
|---|---|---|
| #12 | Ferreira (`Druitti`) | Desenho + 6 katas com testes |
| #13 | Santiago (`gabsant07`) | Script de cronometragem / CSV |
| #14 | Tavares (`Tavaresds1`) | Ambiente + Radon |

```bash
pip install -r requirements.txt
pytest lab02/katas/reference/test_reference.py -q   # valida gabarito (grupo)
cd lab02/katas/k1_merge_intervals && pytest -q      # trial (deve falhar ate implementar)
```

### Cronometragem dos trials (Issue #13)

Execute o comando abaixo na raiz do projeto e mantenha o terminal aberto durante o trial:

```bash
python lab02/scripts/timer_trial.py --integrante gabsant07 --kata k1_merge_intervals --tratamento com_ia
```

Valores aceitos em `--tratamento`: `com_ia` e `sem_ia`. O script verifica os testes
automaticamente, encerra ao atingir o green ou após 35 minutos e acrescenta o resultado em
`lab02/data/trials.csv`. Trials que não atingem o green são registrados como censurados.

Os arquivos `kata.py` começam incompletos de propósito e devem ser implementados durante cada
trial. Interromper com `Ctrl+C` cancela a execução sem registrar uma medição inválida. Instruções
detalhadas: [lab02/scripts/README.md](lab02/scripts/README.md).

### Métricas estáticas dos trials (Issue #14)

Logo após o trial terminar, antes de o próximo integrante sobrescrever o mesmo `kata.py`, rode:

```bash
python lab02/scripts/static_metrics.py --integrante gabsant07 --kata k1_merge_intervals --tratamento com_ia --mi
```

O script calcula LOC e complexidade ciclomática (via Radon) do `kata.py` medido, adiciona
opcionalmente o Índice de Manutenibilidade (`--mi`) e acrescenta o resultado em
`lab02/data/static_metrics.csv`. Detalhes e a decisão sobre duplicação de código:
[docs/lab02/ambiente.md](docs/lab02/ambiente.md).
