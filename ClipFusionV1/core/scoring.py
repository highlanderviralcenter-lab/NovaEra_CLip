"""
ClipFusionV1.core.scoring
=========================

Implementa uma heurística simples para atribuição de notas de viralidade
a segmentos de vídeo.  Esta versão baseia‑se apenas na posição do
segmento no vídeo, atribuindo pontuações mais altas para os
primeiros cortes, sob a premissa de que espectadores tendem a
abandonar vídeos longos.  Futuras versões podem integrar dados
reais de engajamento ou modelos de aprendizado.
"""

from __future__ import annotations

from typing import List


def score_segments(segments: List[tuple[float, float]]) -> List[float]:
    """Gera uma lista de scores (0‑100) para cada segmento.

    A pontuação inicial é 80 para o primeiro segmento e decresce em
    passos fixos para os subsequentes.  O valor mínimo é 20.

    Parameters
    ----------
    segments: List[Tuple[float, float]]
        Lista de segmentos (início, fim).

    Returns
    -------
    List[float]
        Lista de pontuações na mesma ordem dos segmentos.
    """
    scores = []
    score = 80.0
    for _ in segments:
        scores.append(max(20.0, score))
        score -= 10.0
    return scores
