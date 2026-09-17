"""K1 — Mesclar intervalos de agenda.

Dado uma lista de intervalos [inicio, fim] (inteiros, inicio <= fim),
retorne a lista de intervalos mesclados (sobrepostos ou adjacentes).

Exemplo:
  merge_intervals([[1,3],[2,6],[8,10],[15,18]]) -> [[1,6],[8,10],[15,18]]
  merge_intervals([[1,4],[4,5]]) -> [[1,5]]
"""

from __future__ import annotations


def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Mescla intervalos sobrepostos ou adjacentes."""
    if not intervals:
        return []

    intervalos_ordenados = sorted(intervals, key=lambda intervalo: intervalo[0])
    resultado = [intervalos_ordenados[0].copy()]

    for inicio, fim in intervalos_ordenados[1:]:
        ultimo = resultado[-1]

        if inicio <= ultimo[1]:
            ultimo[1] = max(ultimo[1], fim)
        else:
            resultado.append([inicio, fim])

    return resultado