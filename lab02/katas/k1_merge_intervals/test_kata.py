from kata import merge_intervals


def test_exemplo_basico():
    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [
        [1, 6],
        [8, 10],
        [15, 18],
    ]


def test_adjacentes():
    assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]


def test_vazio():
    assert merge_intervals([]) == []


def test_um_intervalo():
    assert merge_intervals([[5, 9]]) == [[5, 9]]


def test_desordenado():
    assert merge_intervals([[8, 10], [1, 3], [2, 6]]) == [[1, 6], [8, 10]]


def test_contido():
    assert merge_intervals([[1, 10], [2, 3], [4, 5]]) == [[1, 10]]
