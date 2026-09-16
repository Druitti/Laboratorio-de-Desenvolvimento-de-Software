"""K5 — Trial Ferreira (sem_ia) — Issue #21."""

from __future__ import annotations


def is_valid_code(code: str) -> bool:
    if len(code) != 8:
        return False
    if not code.isdigit():
        return False
    soma = 0
    for ch in code[:7]:
        soma += int(ch)
    dv = (soma * 3) % 10
    return int(code[7]) == dv
