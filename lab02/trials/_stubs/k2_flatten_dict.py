"""K2 — Achatar dicionário aninhado com chaves pontuadas.

Exemplo:
  flatten_dict({"a": 1, "b": {"c": 2, "d": {"e": 3}}})
  -> {"a": 1, "b.c": 2, "b.d.e": 3}
"""

from __future__ import annotations

from typing import Any


def flatten_dict(data: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """Achata dict aninhado; valores não-dict são folhas."""
    raise NotImplementedError("Implemente flatten_dict durante o trial")
