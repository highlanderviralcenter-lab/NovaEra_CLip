"""
SignalCut Hybrid — Candidate Engine
Score local dos segmentos usando heurísticas de linguagem
e os 10 arquétipos emocionais definidos em scoring.yaml
"""

import re
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


_SCORING_PATH = Path(__file__).parent.parent / "data" / "scoring.yaml"
_config_cache: Optional[Dict] = None


def _load_config() -> Dict:
    global _config_cache
    if _config_cache is None:
        with open(_SCORING_PATH, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


# ─── Scoring de Hook ──────────────────────────────────────────────────────────

def score_hook(text: str, start_time: float, duration: float) -> float:
    """
    Avalia o poder de gancho do trecho.
    Prioriza os primeiros 3 segundos do segmento.

    Fatores:
    - Padrões linguísticos de hook (pergunta, número, imperativo)
    - Arquétipo detectado e seu bonus de hook
    - Posição no segmento (texto inicial tem mais peso)
    """
    cfg = _load_config()
    score = 0.0

    # Pega os primeiros ~40 chars (representa ~3s de fala)
    hook_text = text[:120].lower()
    full_text  = text.lower()

    # Padrões estruturais de hook
    for pattern_name, pdata in cfg.get("hook_patterns", {}).items():
        pat = pdata.get("pattern", "")
        bonus = float(pdata.get("bonus", 0.0))
        try:
            if re.search(pat, hook_text, re.IGNORECASE):
                score += bonus
        except re.error:
            pass

    # Arquétipo dominante — contribui com hook_bonus
    archetype, arch_score = detect_archetype(text)
    if archetype:
        arch_cfg = cfg.get("archetypes", {}).get(archetype, {})
        score += float(arch_cfg.get("hook_bonus", 0.0)) * arch_score

    # Penalidade por começo suave (sem impacto)
    soft_starters = ["então", "bom", "como eu disse", "vamos falar", "hoje vou"]
    for starter in soft_starters:
        if hook_text.startswith(starter):
            score -= 0.08
            break

    # Bônus por densidade de informação nas primeiras palavras
    words_first = len(hook_text.split())
    if words_first >= 8:
        score += 0.05

    return min(max(round(score, 4), 0.0), 1.0)


# ─── Scoring de Retenção ──────────────────────────────────────────────────────

def score_retention(text: str, segments_in_window: List[Dict]) -> float:
    """
    Avalia o arco narrativo e conectivos de continuidade.

    Busca por:
    - Conectivos de tensão/virada
    - Progressão lógica (setup → conflito → resolução)
    - Variação de ritmo (frases curtas após longas = aceleração)
    """
    cfg = _load_config()
    score = 0.0
    text_lower = text.lower()

    # Conectivos de retenção
    connectives = cfg.get("retention_connectives", [])
    found = sum(1 for c in connectives if c in text_lower)
    score += min(found * 0.06, 0.30)

    # Variação de comprimento de frase (ritmo narrativo)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 3:
        lengths = [len(s.split()) for s in sentences]
        variance = _variance(lengths)
        if variance > 10:
            score += 0.10
        elif variance > 5:
            score += 0.05

    # Presença de arco completo (setup + conflito + resolução)
    has_setup    = any(w in text_lower for w in ["era", "estava", "tinha", "vivia"])
    has_conflict = any(w in text_lower for w in ["mas", "porém", "aí", "problema", "difícil"])
    has_resolve  = any(w in text_lower for w in ["então", "resultado", "consegui", "funcionou", "mudou"])
    arc_score = sum([has_setup, has_conflict, has_resolve]) / 3
    score += arc_score * 0.25

    # Coesão entre segmentos da janela
    if len(segments_in_window) >= 2:
        all_text = " ".join(s.get("text", "") for s in segments_in_window).lower()
        coesion_markers = ["isso", "esse", "essa", "portanto", "assim", "logo"]
        coesion = sum(1 for m in coesion_markers if m in all_text)
        score += min(coesion * 0.03, 0.10)

    return min(max(round(score, 4), 0.0), 1.0)


# ─── Scoring de Momento ───────────────────────────────────────────────────────

def score_moment(text: str) -> float:
    """
    Detecta clímax, virada ou punchline — o "momento humano orgânico".

    Busca por:
    - Exclamações e ênfase emocional
    - Revelações inesperadas
    - Contraste extremo (era X, virou Y)
    """
    score = 0.0
    text_lower = text.lower()

    # Ênfase emocional
    exclamations = text.count("!")
    score += min(exclamations * 0.05, 0.15)

    # Palavras de revelação/virada
    revelation_words = [
        "descobri", "percebi", "entendi", "foi aí", "de repente",
        "mas aí", "e então", "inacreditável", "nunca imaginei",
        "surpreendente", "chocante", "impressionante"
    ]
    for word in revelation_words:
        if word in text_lower:
            score += 0.08
            break

    # Contraste antes/depois
    contrast_pairs = [
        ("antes", "depois"), ("era", "agora"), ("tinha", "tenho"),
        ("perdi", "ganhei"), ("fracasso", "sucesso"), ("ruim", "bom")
    ]
    for (a, b) in contrast_pairs:
        if a in text_lower and b in text_lower:
            score += 0.12
            break

    # Punchline curta no final (frase final com menos de 10 palavras)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if sentences:
        last = sentences[-1].split()
        if 3 <= len(last) <= 10:
            score += 0.08

    # Aliteração ou paralelismo (padrão rítmico)
    words = text_lower.split()
    if len(words) >= 6:
        starts = [w[0] for w in words if len(w) > 3]
        most_common_start = max(set(starts), key=starts.count) if starts else ""
        if starts.count(most_common_start) >= 3:
            score += 0.05

    return min(max(round(score, 4), 0.0), 1.0)


# ─── Scoring de Shareability ──────────────────────────────────────────────────

def score_shareability(text: str) -> float:
    """
    Estima potencial de recompartilhamento.

    Alto shareability = conteúdo que as pessoas PRECISAM mandar pra alguém.
    """
    score = 0.0
    text_lower = text.lower()

    # Conteúdo com referência "você vai querer mandar pra alguém"
    share_triggers = [
        "manda pra quem", "tag alguém", "você conhece alguém",
        "passa pra frente", "compartilha", "mostra pro",
        "salva esse", "guarda esse"
    ]
    for t in share_triggers:
        if t in text_lower:
            score += 0.20
            break

    # Conteúdo universalmente relatable (todo mundo se identifica)
    relatable = [
        "todo mundo", "todos nós", "quem nunca", "você também",
        "a maioria das pessoas", "muita gente", "você com certeza"
    ]
    for r in relatable:
        if r in text_lower:
            score += 0.12
            break

    # Controver­sial mas não ofensivo (gera comentários)
    controversial = [
        "discordo", "polêmico", "dividido", "opinião impopular",
        "vai me xingar", "pode me cancelar", "vou ser honesto"
    ]
    for c in controversial:
        if c in text_lower:
            score += 0.10
            break

    # Dado/número específico aumenta credibilidade e compartilhamento
    if re.search(r'\b\d+[%°$]?\b', text):
        score += 0.08

    # CTA explícito de compartilhamento
    if re.search(r'(salva|compartilha|segue|marca|comenta)', text_lower):
        score += 0.10

    return min(max(round(score, 4), 0.0), 1.0)


# ─── Platform Fit ─────────────────────────────────────────────────────────────

def score_platform_fit(duration: float, archetype: str) -> Dict[str, float]:
    """
    Calcula adequação às regras de cada plataforma.

    TikTok:    15-60s, conteúdo emocionalmente intenso
    Reels:     15-90s, visual e dinâmico
    Shorts:    15-60s, informativo/educacional
    """
    cfg = _load_config()

    def _duration_fit(dur: float, min_s: float, max_s: float, ideal: float) -> float:
        if dur < min_s or dur > max_s:
            return 0.3
        dist = abs(dur - ideal) / (max_s - min_s)
        return round(max(0.5, 1.0 - dist), 3)

    arch_cfg = cfg.get("archetypes", {}).get(archetype or "", {})
    arch_platforms = arch_cfg.get("platforms", ["tiktok", "reels", "shorts"])

    fits = {}
    platform_rules = {
        "tiktok":  {"min": 15, "max": 60,  "ideal": 27},
        "reels":   {"min": 15, "max": 90,  "ideal": 30},
        "shorts":  {"min": 15, "max": 60,  "ideal": 45},
    }
    for plat, rules in platform_rules.items():
        base = _duration_fit(duration, rules["min"], rules["max"], rules["ideal"])
        arch_bonus = 0.10 if plat in arch_platforms else 0.0
        fits[plat] = min(round(base + arch_bonus, 3), 1.0)

    return fits


# ─── Arquétipo ────────────────────────────────────────────────────────────────

def detect_archetype(text: str) -> Tuple[str, float]:
    """
    Detecta o arquétipo emocional dominante no texto.
    Retorna (nome_arquetipo, score_normalizado).
    """
    cfg = _load_config()
    text_lower = text.lower()

    best_arch  = ""
    best_score = 0.0

    for arch_name, arch_data in cfg.get("archetypes", {}).items():
        weight    = float(arch_data.get("weight", 0.2))
        triggers  = arch_data.get("triggers", [])
        hits = sum(1 for t in triggers if t in text_lower)
        if hits == 0:
            continue
        raw = weight * (1 + math.log(1 + hits) * 0.3)
        if raw > best_score:
            best_score = raw
            best_arch  = arch_name

    return best_arch, round(min(best_score, 1.0), 4)


# ─── Duration Fit ─────────────────────────────────────────────────────────────

def score_duration_fit(duration: float) -> float:
    """
    Pontuação baseada na "faixa de ouro" (18-35s).
    Penaliza segmentos muito curtos ou muito longos.
    """
    cfg = _load_config()
    dur_cfg = cfg.get("duration", {})
    min_s   = float(dur_cfg.get("min_seconds", 18))
    max_s   = float(dur_cfg.get("max_seconds", 35))
    ideal   = float(dur_cfg.get("ideal_seconds", 27))
    pen_over  = float(dur_cfg.get("penalty_per_second_over", 0.05))
    pen_under = float(dur_cfg.get("penalty_per_second_under", 0.08))

    if min_s <= duration <= max_s:
        dist = abs(duration - ideal)
        return round(max(0.7, 1.0 - dist * 0.02), 4)
    elif duration < min_s:
        return round(max(0.0, 0.7 - (min_s - duration) * pen_under), 4)
    else:
        return round(max(0.0, 0.7 - (duration - max_s) * pen_over), 4)


# ─── Combined Score ───────────────────────────────────────────────────────────

def compute_combined_score(
    hook: float,
    retention: float,
    moment: float,
    shareability: float,
    platform_fits: Dict[str, float],
) -> float:
    """
    Combina todas as subnotas com os pesos do scoring.yaml.
    """
    cfg     = _load_config()
    weights = cfg.get("combined_weights", {})

    avg_platform = sum(platform_fits.values()) / max(len(platform_fits), 1)

    combined = (
        hook         * float(weights.get("hook_strength",    0.30)) +
        retention    * float(weights.get("retention_score",  0.25)) +
        moment       * float(weights.get("moment_strength",  0.20)) +
        shareability * float(weights.get("shareability",     0.15)) +
        avg_platform * float(weights.get("platform_fit",     0.10))
    )
    return round(min(combined * 10, 10.0), 4)  # escala 0-10


# ─── Entry Point ──────────────────────────────────────────────────────────────

def score_candidate(
    text: str,
    start_time: float,
    end_time: float,
    segments_in_window: List[Dict],
    transcription_quality: float = 1.0,
) -> Dict:
    """
    Pontua um candidato completo.
    Retorna dict com todas as subnotas e combined_score.
    """
    duration = end_time - start_time

    archetype, arch_score = detect_archetype(text)
    hook         = score_hook(text, start_time, duration)
    retention    = score_retention(text, segments_in_window)
    moment       = score_moment(text)
    shareability = score_shareability(text)
    platform_fits = score_platform_fit(duration, archetype)
    duration_fit = score_duration_fit(duration)
    combined     = compute_combined_score(hook, retention, moment, shareability, platform_fits)

    # Penaliza por qualidade baixa de transcrição
    if transcription_quality < 0.7:
        combined *= transcription_quality

    return {
        "archetype":            archetype,
        "archetype_score":      arch_score,
        "hook_strength":        hook,
        "retention_score":      retention,
        "moment_strength":      moment,
        "shareability":         shareability,
        "platform_fit_tiktok":  platform_fits.get("tiktok",  0.0),
        "platform_fit_reels":   platform_fits.get("reels",   0.0),
        "platform_fit_shorts":  platform_fits.get("shorts",  0.0),
        "duration_fit":         duration_fit,
        "combined_score":       combined,
    }


# ─── Utils ────────────────────────────────────────────────────────────────────

def _variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)
