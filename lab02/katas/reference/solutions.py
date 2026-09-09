"""Soluções de referência — NÃO abrir durante os trials do experimento."""

def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda x: x[0])
    merged = [ordered[0][:]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def flatten_dict(data, parent_key="", sep="."):
    items = {}
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key, sep=sep))
        else:
            items[new_key] = value
    return items


def errors_by_hour(lines):
    counts = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        time_part = parts[1]
        level = parts[2]
        if level not in {"ERROR", "FATAL"}:
            continue
        hour = time_part.split(":")[0]
        counts[hour] = counts.get(hour, 0) + 1
    return counts


def longest_free_streak(parking):
    best = cur = 0
    for slot in parking:
        if slot == 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def is_valid_code(code):
    if len(code) != 8 or not code.isdigit():
        return False
    total = sum(int(d) for d in code[:7])
    return int(code[7]) == (total * 3) % 10


def frame_score(frames):
    total = 0
    n = len(frames)
    for i, pins in enumerate(frames):
        if pins == 10:
            bonus = 0
            if i + 1 < n:
                bonus += frames[i + 1]
            if i + 2 < n:
                bonus += frames[i + 2]
            total += 10 + bonus
        else:
            total += pins
    return total
