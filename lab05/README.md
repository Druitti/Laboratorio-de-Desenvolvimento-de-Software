# Lab05 — SQLite: journal WAL × rollback

Experimento controlado com o SQLite em operação: a mesma versão mantida em produção
(3.54.1), rodando localmente, com o modo de journal variando entre DELETE (padrão) e WAL.
Proposta, hipóteses, GQM e as 7 categorias: [proposta](../docs/lab05/proposta.md) (#74).

## Piloto (Lab05S01)

Na raiz do repositório, com Python 3.12 ou superior (só biblioteca padrão):

```bash
python -m lab05.pilot
```

Roda 10 rodadas com as 4 condições (modo × carga) em ordem sorteada (semente 5), cada uma
num banco novo, e grava `lab05/data/pilot.csv` e `lab05/data/pilot_env.json`. Use
`--rounds`, `--seed`, `--write-transactions`, `--read-rows` e `--read-queries` para mudar o
tamanho. A versão do SQLite medida é a do módulo `sqlite3` do Python usado, e fica registrada
no JSON.

## Testes

```bash
python -m pip install pytest
python -m pytest lab05/tests -q
```
