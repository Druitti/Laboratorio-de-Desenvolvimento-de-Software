"""K3 — Contagem de erros em log por hora.

Cada linha no formato: 'YYYY-MM-DD HH:MM:SS LEVEL message'
Considere ERROR e FATAL como erro. Retorne dict hora -> quantidade
(hora = 'HH' com dois dígitos).

Exemplo de linha: '2026-09-09 14:03:11 ERROR disco cheio'
"""

from __future__ import annotations


def errors_by_hour(lines: list[str]) -> dict[str, int]:
    resultado = {}

    for linha in lines:
        partes = linha.split()

        nivel = partes[2]

        if nivel == "ERROR" or nivel == "FATAL":
            horario = partes[1]
            hora = horario.split(":")[0]

            if hora in resultado:
                resultado[hora] = resultado[hora] + 1
            else:
                resultado[hora] = 1

    return resultado