"""K4 — Trial Ferreira (sem_ia) — Issue #20."""

from __future__ import annotations


def longest_free_streak(parking: list[int]) -> int:
    best = 0
    current = 0
    for spot in parking:
        if spot == 0:
            current += 1
            if current > best:
                best = current
        else:
            current = 0
    return best
