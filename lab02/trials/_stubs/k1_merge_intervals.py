"""K1 — Mesclar intervalos de agenda.

Dado uma lista de intervalos [inicio, fim] (inteiros, inicio <= fim),
retorne a lista de intervalos mesclados (sobrepostos ou adjacentes).

Exemplo:
  merge_intervals([[1,3],[2,6],[8,10],[15,18]]) -> [[1,6],[8,10],[15,18]]
  merge_intervals([[1,4],[4,5]]) -> [[1,5]]
"""

from __future__ import annotations


def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Mescla intervalos sobrepostos/adjacentes e devolve ordenados por início."""
    raise NotImplementedError("Implemente merge_intervals durante o trial")
