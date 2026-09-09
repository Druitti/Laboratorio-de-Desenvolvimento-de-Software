from kata import errors_by_hour


def test_basico():
    lines = [
        "2026-09-09 14:03:11 ERROR disco cheio",
        "2026-09-09 14:10:00 INFO ok",
        "2026-09-09 15:01:00 FATAL crash",
        "2026-09-09 15:02:00 ERROR x",
    ]
    assert errors_by_hour(lines) == {"14": 1, "15": 2}


def test_vazio():
    assert errors_by_hour([]) == {}


def test_sem_erros():
    assert errors_by_hour(["2026-09-09 08:00:00 INFO hi"]) == {}


def test_warning_nao_conta():
    assert errors_by_hour(["2026-09-09 09:00:00 WARN cuidado"]) == {}


def test_mesma_hora():
    lines = [
        "2026-01-01 00:00:01 ERROR a",
        "2026-01-01 00:59:59 FATAL b",
    ]
    assert errors_by_hour(lines) == {"00": 2}
