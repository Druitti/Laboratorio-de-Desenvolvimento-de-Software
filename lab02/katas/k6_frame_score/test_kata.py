from kata import frame_score


def test_sem_strike():
    assert frame_score([3, 5, 2]) == 10


def test_strike_com_bonus():
    assert frame_score([10, 3, 4]) == 10 + 3 + 4 + 3 + 4  # 24


def test_strike_final_sem_bonus():
    assert frame_score([2, 10]) == 2 + 10


def test_vazio():
    assert frame_score([]) == 0


def test_varios_strikes():
    # [10,10,5] -> (10+10+5) + (10+5) + 5 = 25+15+5 = 45
    assert frame_score([10, 10, 5]) == 45
