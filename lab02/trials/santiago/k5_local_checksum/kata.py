"""K5 — Código de verificação local (checksum).

Dado um código com 7 dígitos (string), o 8º dígito verificador é:
  (soma dos 7 dígitos * 3) mod 10

is_valid_code("1234567X") é True sse X == dígito verificador correto.

Exemplo: dígitos 1+2+3+4+5+6+7 = 28; (28*3)%10 = 4 → "12345674" válido.
"""

from __future__ import annotations


def is_valid_code(code: str) -> bool:
    if len(code) != 8:
        return False

    if not code.isdigit():
        return False

    soma = 0

    for numero in code[:7]:
        soma = soma + int(numero)

    digito_correto = (soma * 3) % 10
    ultimo_digito = int(code[7])

    if ultimo_digito == digito_correto:
        return True
    else:
        return False