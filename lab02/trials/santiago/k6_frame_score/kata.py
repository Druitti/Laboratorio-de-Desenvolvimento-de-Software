"""K6 — Pontuação simplificada de frames.

Cada frame é um inteiro 0..10 (pinos derrubados naquela jogada única).
A pontuação de um frame i é:
  - se frames[i] == 10 (strike): 10 + frames[i+1] + frames[i+2] (se existirem)
  - senão: frames[i]

Some a pontuação de todos os frames da lista.
Frames sem "próximos" suficientes para o bônus de strike somam apenas 10.
"""

from __future__ import annotations


def frame_score(frames: list[int]) -> int:
    total = 0

    for i in range(len(frames)):
        total = total + frames[i]

        if frames[i] == 10:
            if i + 1 < len(frames):
                total = total + frames[i + 1]

            if i + 2 < len(frames):
                total = total + frames[i + 2]

    return total