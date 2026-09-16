"""K3 — Contagem de erros em log por hora.

Cada linha no formato: 'YYYY-MM-DD HH:MM:SS LEVEL message'
Considere ERROR e FATAL como erro. Retorne dict hora -> quantidade
(hora = 'HH' com dois dígitos).

Exemplo de linha: '2026-09-09 14:03:11 ERROR disco cheio'
"""

from __future__ import annotations


def errors_by_hour(lines: list[str]) -> dict[str, int]:
    """Conta erros (ERROR/FATAL) agrupados pela hora do timestamp."""
    raise NotImplementedError("Implemente errors_by_hour durante o trial")
