from __future__ import annotations

def frame_score(quadros: list[int]) -> int:
    """Calcula pontuação total da sequência de frames simplificada."""
    pontuacao_total = 0
    total_quadros = len(quadros)
    for indice, pinos in enumerate(quadros):
        if pinos == 10:
            bonus_strike = pinos            
            if indice + 1 < total_quadros:
                bonus_strike += quadros[indice + 1]                
            if indice + 2 < total_quadros:
                bonus_strike += quadros[indice + 2]
            pontuacao_total += bonus_strike
        else:
            pontuacao_total += pinos
    return pontuacao_total