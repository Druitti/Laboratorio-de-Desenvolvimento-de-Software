"""K1 — Trial Ferreira (com_ia) — Issue #17."""

from __future__ import annotations


def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Mescla intervalos sobrepostos ou adjacentes, ordenados pelo início."""
    if not intervals:
        return []

    ordered = sorted((interval[:] for interval in intervals), key=lambda item: item[0])
    result = [ordered[0]]

    for start, end in ordered[1:]:
        last_start, last_end = result[-1]
        if start <= last_end:
            result[-1][1] = max(last_end, end)
        else:
            result.append([start, end])

    return result
