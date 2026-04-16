"""
SignalCut Hybrid — Segmentador
Micro-segmentação baseada em pausas naturais e limites de fala.
NÃO usa janelas fixas — respeita o ritmo do conteúdo.

Faixa alvo: 18-35 segundos (faixa de ouro para short-form)
"""

from typing import List, Dict, Tuple, Optional
import re


# ─── Configuração ─────────────────────────────────────────────────────────────

MIN_DURATION   = 15.0   # segundos — descarta segmentos muito curtos
MAX_DURATION   = 45.0   # segundos — força quebra se muito longo
IDEAL_MIN      = 18.0
IDEAL_MAX      = 35.0
SILENCE_GAP    = 0.6    # pausa ≥ 0.6s entre segmentos = ponto de corte natural
MIN_WORDS      = 25     # mínimo de palavras para um candidato viável
MAX_WORDS      = 120    # máximo antes de forçar corte


# ─── Funções Públicas ─────────────────────────────────────────────────────────

def segment_transcript(
    segments: List[Dict],
    min_duration: float = MIN_DURATION,
    max_duration: float = MAX_DURATION,
    silence_gap: float = SILENCE_GAP,
) -> List[Dict]:
    """
    Agrupa segmentos Whisper em janelas candidatas baseadas em:
    1. Pausas naturais de fala (gap entre segmentos)
    2. Limites de duração (18-35s alvo)
    3. Limites semânticos (fim de frase/parágrafo)

    Retorna lista de candidatos com start, end, text, n_segments.
    """
    if not segments:
        return []

    # Normaliza os segmentos
    segs = _normalize_segments(segments)
    if not segs:
        return []

    candidates = []
    window_start_idx = 0

    for i in range(len(segs)):
        window_segs = segs[window_start_idx : i + 1]
        duration = window_segs[-1]["end"] - window_segs[0]["start"]

        # Verifica se deve fechar a janela aqui
        should_close = False
        reason = ""

        # 1. Duração atingiu máximo — fecha aqui
        if duration >= max_duration:
            should_close = True
            reason = "max_duration"

        # 2. Pausa natural após este segmento — candidato a fechamento
        elif i < len(segs) - 1:
            gap = segs[i + 1]["start"] - segs[i]["end"]
            if gap >= silence_gap and duration >= min_duration:
                should_close = True
                reason = "silence_gap"

            # Fim de frase forte na duração ideal
            elif _ends_sentence(segs[i]["text"]) and IDEAL_MIN <= duration <= IDEAL_MAX:
                should_close = True
                reason = "sentence_boundary"

        # 3. Último segmento
        elif i == len(segs) - 1 and duration >= min_duration:
            should_close = True
            reason = "end_of_transcript"

        if should_close:
            candidate = _build_candidate(window_segs, reason)
            if candidate:
                candidates.append(candidate)
            window_start_idx = i + 1

    # Fragmento restante
    remaining = segs[window_start_idx:]
    if remaining:
        duration = remaining[-1]["end"] - remaining[0]["start"]
        if duration >= min_duration:
            candidate = _build_candidate(remaining, "remainder")
            if candidate:
                candidates.append(candidate)

    # Remove sobreposições e ordena
    candidates = _deduplicate(candidates)
    candidates.sort(key=lambda c: c["start"])

    # Adiciona índice
    for idx, c in enumerate(candidates):
        c["segment_index"] = idx

    return candidates


def get_segments_in_window(
    all_segments: List[Dict],
    start: float,
    end: float,
) -> List[Dict]:
    """
    Retorna segmentos Whisper dentro de uma janela de tempo.
    Usado pelo candidate_engine para análise de contexto.
    """
    return [
        s for s in all_segments
        if s.get("start", 0) >= start and s.get("end", 0) <= end
    ]


def find_natural_cut_point(
    segments: List[Dict],
    target_start: float,
    target_end: float,
    tolerance: float = 2.0,
) -> Tuple[float, float]:
    """
    Ajusta start/end para o ponto de pausa natural mais próximo.
    Evita cortar no meio de uma palavra ou frase.

    Tolerância: até 2 segundos de ajuste.
    """
    best_start = target_start
    best_end   = target_end

    # Ajusta start para início do segmento mais próximo
    for seg in segments:
        seg_start = seg.get("start", 0)
        if abs(seg_start - target_start) <= tolerance:
            if abs(seg_start - target_start) < abs(best_start - target_start):
                best_start = seg_start

    # Ajusta end para fim do segmento mais próximo
    for seg in segments:
        seg_end = seg.get("end", 0)
        if abs(seg_end - target_end) <= tolerance:
            if abs(seg_end - target_end) < abs(best_end - target_end):
                best_end = seg_end

    # Garante mínimo de 10s
    if best_end - best_start < 10.0:
        best_end = best_start + target_end - target_start

    return round(best_start, 3), round(best_end, 3)


# ─── Funções Internas ─────────────────────────────────────────────────────────

def _normalize_segments(segments: List[Dict]) -> List[Dict]:
    """Garante que todos os segmentos têm start, end, text válidos."""
    result = []
    for seg in segments:
        start = float(seg.get("start", 0))
        end   = float(seg.get("end", start))
        text  = str(seg.get("text", "")).strip()
        if end > start and text:
            result.append({"start": start, "end": end, "text": text})
    return sorted(result, key=lambda s: s["start"])


def _build_candidate(window_segs: List[Dict], reason: str) -> Optional[Dict]:
    """Constrói um candidato a partir de uma janela de segmentos."""
    if not window_segs:
        return None

    start    = window_segs[0]["start"]
    end      = window_segs[-1]["end"]
    duration = end - start
    text     = " ".join(s["text"] for s in window_segs).strip()
    n_words  = len(text.split())

    if n_words < MIN_WORDS:
        return None
    if duration < MIN_DURATION:
        return None

    return {
        "start":       round(start, 3),
        "end":         round(end, 3),
        "duration":    round(duration, 3),
        "text":        text,
        "n_segments":  len(window_segs),
        "n_words":     n_words,
        "close_reason": reason,
        "in_golden_range": IDEAL_MIN <= duration <= IDEAL_MAX,
    }


def _ends_sentence(text: str) -> bool:
    """Verifica se o texto termina com pontuação de fim de frase."""
    text = text.strip()
    return bool(text) and text[-1] in ".!?…"


def _deduplicate(candidates: List[Dict]) -> List[Dict]:
    """
    Remove candidatos sobrepostos.
    Em caso de sobreposição, mantém o que está mais próximo da faixa ideal.
    """
    if len(candidates) <= 1:
        return candidates

    result = [candidates[0]]
    for cand in candidates[1:]:
        prev = result[-1]
        # Sobreposição: este candidato começa antes do anterior terminar
        if cand["start"] < prev["end"] - 1.0:
            # Mantém o que tem melhor duration_fit
            prev_fit = _duration_fitness(prev["duration"])
            cand_fit = _duration_fitness(cand["duration"])
            if cand_fit > prev_fit:
                result[-1] = cand
        else:
            result.append(cand)

    return result


def _duration_fitness(duration: float) -> float:
    """Score de adequação à faixa ideal de duração."""
    if IDEAL_MIN <= duration <= IDEAL_MAX:
        return 1.0 - abs(duration - (IDEAL_MIN + IDEAL_MAX) / 2) / (IDEAL_MAX - IDEAL_MIN)
    elif duration < IDEAL_MIN:
        return max(0.0, (duration - MIN_DURATION) / (IDEAL_MIN - MIN_DURATION))
    else:
        return max(0.0, (MAX_DURATION - duration) / (MAX_DURATION - IDEAL_MAX))
