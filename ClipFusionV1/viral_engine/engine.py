"""
ClipFusionV1.viral_engine.engine
================================

Contém classes para análise de nicho, geração de ganchos e
recomendações de cronogramas de publicação.  Estes componentes
trabalham de forma independente para que possam ser facilmente
substituídos por modelos mais sofisticados no futuro.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List, Dict


class ViralAnalyzer:
    """Detecta nichos e gera hooks com base em texto de transcrição."""

    def __init__(self) -> None:
        # Lista de nichos suportados; os valores podem ser expandidos
        self.niches = [
            "investimentos",
            "fitness",
            "tecnologia",
            "relacionamentos",
            "empreendedorismo",
        ]
        # Arquétipos emocionais usados para classificação.
        self.archetypes = [
            "Urgência",
            "Inspiracional",
            "Curiosidade",
            "Autoridade",
            "Humor",
            "Controvérsia",
            "Empatia",
            "Utilidade",
            "FOMO",
            "Prova Social",
        ]

    def detect_niche(self, transcription_text: str) -> str:
        text_lower = transcription_text.lower()
        for n in self.niches:
            if n in text_lower:
                return n
        return "geral"

    def generate_hooks(self, clip_segment_text: str) -> Dict[str, str]:
        """Gera três variações de hooks para o segmento."""
        snippet = clip_segment_text.strip()[:30] or "seu tema"
        return {
            "hook_direct": f"Você precisa saber sobre {snippet}...",
            "hook_curiosity": f"Descubra o segredo de {snippet}...",
            "hook_challenge": f"Desafie‑se: pare de ignorar {snippet}!",
        }

    def pick_archetype(self, index: int) -> str:
        """Escolhe um arquétipo baseado no índice do segmento."""
        return self.archetypes[index % len(self.archetypes)]


class Schedulyzer:
    """Gera cronogramas anti‑padrão e recomenda plataformas."""

    def __init__(self) -> None:
        # Horários padrão que serão embaralhados por jitter
        self.standard_slots = ["09:00", "12:00", "18:00", "21:00"]

    def generate_schedule(self, target_date: datetime.date) -> List[str]:
        schedules: List[str] = []
        for slot in self.standard_slots:
            h, m = map(int, slot.split(":"))
            jitter_m = random.randint(3, 14)
            jitter_s = random.randint(1, 59)
            post_time = datetime.combine(target_date, datetime.min.time())
            post_time = post_time.replace(hour=h, minute=m)
            post_time += timedelta(minutes=jitter_m, seconds=jitter_s)
            schedules.append(post_time.strftime("%H:%M:%S"))
        return schedules

    def recommend_platform(self, niche: str, viral_score: float) -> str:
        """Recomenda uma plataforma com base no nicho e score."""
        if niche == "investimentos" and viral_score > 80:
            return "Reels / LinkedIn"
        return "TikTok / Shorts"
