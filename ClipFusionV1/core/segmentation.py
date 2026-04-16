"""
ClipFusionV1.core.segmentation
==============================

Algoritmos simples de segmentação de vídeos.  A versão atual divide
o vídeo em segmentos de tamanho máximo fixo (60 segundos por padrão),
pois não há acesso a redes neurais para detecção automática de
cortes.  Uma heurística baseada no tempo total do vídeo é aplicada
para criar intervalos uniformes.  Futuras versões podem usar
diferentes critérios, como silencios ou análise semântica.
"""

from __future__ import annotations

import subprocess
from typing import List, Tuple

from .utils import get_video_duration


def segment(video_path: str, max_duration: float = 60.0) -> List[Tuple[float, float]]:
    """Divide o vídeo em segmentos de duração máxima.

    Parameters
    ----------
    video_path: str
        Caminho para o arquivo de vídeo.
    max_duration: float
        Duração máxima (em segundos) de cada segmento.

    Returns
    -------
    List[Tuple[float, float]]
        Uma lista de tuplas (início, fim) representando os segmentos.
    """
    total_duration = get_video_duration(video_path)
    if total_duration == 0:
        return [(0.0, max_duration)]
    segments: List[Tuple[float, float]] = []
    start = 0.0
    while start < total_duration:
        end = min(start + max_duration, total_duration)
        segments.append((start, end))
        start = end
    return segments
