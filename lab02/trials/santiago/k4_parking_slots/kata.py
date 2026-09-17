"""K4 — Maior sequência de vagas livres.

parking é uma lista de 0 (livre) e 1 (ocupada).
Retorne o comprimento da maior sequência consecutiva de 0s.
"""

from __future__ import annotations


def longest_free_streak(parking: list[int]) -> int:
    maior_sequencia = 0
    sequencia_atual = 0

    for vaga in parking:
        if vaga == 0:
            sequencia_atual = sequencia_atual + 1

            if sequencia_atual > maior_sequencia:
                maior_sequencia = sequencia_atual
        else:
            sequencia_atual = 0

    return maior_sequencia