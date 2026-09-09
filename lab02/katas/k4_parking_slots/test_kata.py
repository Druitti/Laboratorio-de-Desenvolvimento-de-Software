from kata import longest_free_streak


def test_basico():
    assert longest_free_streak([1, 0, 0, 1, 0, 0, 0, 1]) == 3


def test_tudo_livre():
    assert longest_free_streak([0, 0, 0]) == 3


def test_tudo_ocupado():
    assert longest_free_streak([1, 1, 1]) == 0


def test_vazio():
    assert longest_free_streak([]) == 0


def test_inicio_e_fim():
    assert longest_free_streak([0, 0, 1, 0]) == 2
