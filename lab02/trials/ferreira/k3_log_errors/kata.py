"""K3 — Trial Ferreira (com_ia) — Issue #19."""

from __future__ import annotations


def errors_by_hour(lines: list[str]) -> dict[str, int]:
    """Conta linhas ERROR/FATAL agrupadas pela hora do timestamp."""
    counts: dict[str, int] = {}

    for line in lines:
        pieces = line.split()
        if len(pieces) < 3:
            continue

        clock = pieces[1]
        level = pieces[2]
        if level not in {"ERROR", "FATAL"}:
            continue

        hour = clock.split(":", 1)[0]
        counts[hour] = counts.get(hour, 0) + 1

    return counts
