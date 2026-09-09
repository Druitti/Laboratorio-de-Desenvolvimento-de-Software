from kata import is_valid_code


def test_valido_exemplo():
    assert is_valid_code("12345674") is True


def test_invalido():
    assert is_valid_code("12345670") is False


def test_tamanho_errado():
    assert is_valid_code("123") is False
    assert is_valid_code("123456789") is False


def test_nao_digitos():
    assert is_valid_code("1234567a") is False
    assert is_valid_code("12a45674") is False


def test_outro_valido():
    # 0*7 = 0 -> (0*3)%10 = 0
    assert is_valid_code("00000000") is True
