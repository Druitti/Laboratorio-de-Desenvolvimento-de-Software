"""K6 — Trial Ferreira (sem_ia) — Issue #22."""

from __future__ import annotations


def frame_score(frames: list[int]) -> int:
    total = 0
    n = len(frames)
    for i, pins in enumerate(frames):
        if pins == 10:
            total += 10
            if i + 1 < n:
                total += frames[i + 1]
            if i + 2 < n:
                total += frames[i + 2]
        else:
            total += pins
    return total
