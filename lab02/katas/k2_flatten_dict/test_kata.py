from kata import flatten_dict


def test_exemplo():
    assert flatten_dict({"a": 1, "b": {"c": 2, "d": {"e": 3}}}) == {
        "a": 1,
        "b.c": 2,
        "b.d.e": 3,
    }


def test_vazio():
    assert flatten_dict({}) == {}


def test_plano():
    assert flatten_dict({"x": 10, "y": 20}) == {"x": 10, "y": 20}


def test_lista_como_folha():
    assert flatten_dict({"a": {"b": [1, 2]}}) == {"a.b": [1, 2]}


def test_sep_custom():
    assert flatten_dict({"a": {"b": 1}}, sep="_") == {"a_b": 1}
