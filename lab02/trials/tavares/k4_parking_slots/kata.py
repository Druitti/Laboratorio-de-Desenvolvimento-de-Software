def longest_free_streak(estacionamento: list[int]) -> int:
    """Maior sequência consecutiva de vagas livres (0)."""
    maior_sequencia = 0
    sequencia_atual = 0
    for vaga in estacionamento:
        if vaga == 0:
            sequencia_atual += 1
            if sequencia_atual > maior_sequencia:
                maior_sequencia = sequencia_atual
        else:
            sequencia_atual = 0
    return maior_sequencia