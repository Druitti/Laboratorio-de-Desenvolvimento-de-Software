def errors_by_hour(lines: list[str]) -> dict[str, int]:
    result = {}

    for line in lines:
        parts = line.split()

        hora = parts[1][:2]
        level = parts[2]

        if level in ("ERROR", "FATAL"):
            result[hora] = result.get(hora, 0) + 1

    return result