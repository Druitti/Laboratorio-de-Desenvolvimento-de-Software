# Lab02 — Katas (objetos experimentais)

Seis exercícios Python com testes `pytest`. Durante o trial, edite apenas `kata.py` da pasta do kata.

| ID | Pasta | Função |
|---|---|---|
| K1 | `k1_merge_intervals` | `merge_intervals` |
| K2 | `k2_flatten_dict` | `flatten_dict` |
| K3 | `k3_log_errors` | `errors_by_hour` |
| K4 | `k4_parking_slots` | `longest_free_streak` |
| K5 | `k5_local_checksum` | `is_valid_code` |
| K6 | `k6_frame_score` | `frame_score` |

## Como rodar os testes de um kata

```bash
cd lab02/katas/k1_merge_intervals
pytest -q
```

## Importante

- `kata.py` começa com `NotImplementedError` — é o arquivo do trial.
- `reference/solutions.py` é gabarito interno do grupo: **não consultar durante trials**.
- Time-box: 35 min (Issue #13 cuidará do registro de tempo).
- Não implemente todos os `kata.py` antes da coleta: isso invalidaria a medição do experimento.
