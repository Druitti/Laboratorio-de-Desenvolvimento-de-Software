"""K2 — Trial Ferreira (com_ia) — Issue #18."""

from __future__ import annotations

from typing import Any


def flatten_dict(
    data: dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> dict[str, Any]:
    """Achata um dicionário aninhado usando chaves compostas."""
    flat: dict[str, Any] = {}

    for key, value in data.items():
        full_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
        if isinstance(value, dict):
            flat.update(flatten_dict(value, full_key, sep=sep))
        else:
            flat[full_key] = value

    return flat
