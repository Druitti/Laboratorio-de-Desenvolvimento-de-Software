"""K2 — Achatar dicionário aninhado com chaves pontuadas.

Exemplo:
  flatten_dict({"a": 1, "b": {"c": 2, "d": {"e": 3}}})
  -> {"a": 1, "b.c": 2, "b.d.e": 3}
"""

from __future__ import annotations

from typing import Any


def flatten_dict(data: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    resultado = {}

    for chave in data:
        valor = data[chave]

        if parent_key == "":
            chave_completa = chave
        else:
            chave_completa = parent_key + sep + chave

        if type(valor) == dict:
            outro_dicionario = flatten_dict(valor, chave_completa, sep)

            for item in outro_dicionario:
                resultado[item] = outro_dicionario[item]
        else:
            resultado[chave_completa] = valor

    return resultado