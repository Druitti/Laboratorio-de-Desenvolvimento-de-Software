def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    if not intervals:
        return []

    intervals = sorted(intervals, key=lambda interval: interval[0])

    merged = [intervals[0][:]]

    for inicio, fim in intervals[1:]:
        ultimo_inicio, ultimo_fim = merged[-1]

        # Sobreposto ou adjacente
        if inicio <= ultimo_fim:
            merged[-1][1] = max(ultimo_fim, fim)
        else:
            merged.append([inicio, fim])

    return merged