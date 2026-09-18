def is_valid_code(code: str) -> bool:
    if len(code) != 8 or not code.isdigit():
        return False

    soma = sum(int(digito) for digito in code[:7])
    verificador = (soma * 3) % 10

    return int(code[7]) == verificador