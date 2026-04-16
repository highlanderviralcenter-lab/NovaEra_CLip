"""
SignalCut Hybrid — Decision Engine
Combina score local + veredito da IA + platform fit + duration + qualidade.
Aplica a Regra de Ouro e classifica cada corte.

Fórmula:
  final = local(50%) + external(30%) + platform(10%) + duration(5%) + quality(5%)
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml


_SCORING_PATH = Path(__file__).parent.parent / "data" / "scoring.yaml"
_config_cache = None


def _load_config() -> Dict:
    global _config_cache
    if _config_cache is None:
        with open(_SCORING_PATH, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


# ─── Classificações ──────────────────────────────────────────────────────────

DECISION_APROVADO  = "aprovado"
DECISION_REWORK    = "rework"
DECISION_DESCARTAR = "descartar"


def classify(final_score: float) -> str:
    cfg = _load_config()
    thresholds = cfg.get("decision_thresholds", {})
    if final_score >= float(thresholds.get("aprovado",  9.0)):
        return DECISION_APROVADO
    elif final_score >= float(thresholds.get("rework",  7.0)):
        return DECISION_REWORK
    else:
        return DECISION_DESCARTAR


# ─── Cálculo Final ────────────────────────────────────────────────────────────

def compute_final_score(
    local_score:            float,
    external_score:         float,
    platform_fit:           float,
    duration_fit:           float,
    transcription_quality:  float,
) -> float:
    """
    Aplica a fórmula da Regra de Ouro.
    Todos os valores de entrada devem estar na escala 0.0-1.0
    exceto external_score que pode estar em 0-10 (será normalizado).
    """
    cfg = _load_config()
    w   = cfg.get("decision_weights", {})

    # Normaliza external_score se vier em escala 0-10
    ext = external_score / 10.0 if external_score > 1.0 else external_score
    loc = local_score / 10.0    if local_score > 1.0    else local_score

    final = (
        loc                   * float(w.get("local_score",           0.50)) +
        ext                   * float(w.get("external_score",        0.30)) +
        platform_fit          * float(w.get("platform_fit",          0.10)) +
        duration_fit          * float(w.get("duration_fit",          0.05)) +
        transcription_quality * float(w.get("transcription_quality", 0.05))
    )

    # Converte de volta para escala 0-10
    return round(min(final * 10.0, 10.0), 4)


def decide_cut(
    candidate: Dict,
    ai_cut: Optional[Dict] = None,
    transcription_quality: float = 1.0,
) -> Dict:
    """
    Toma a decisão final para um corte.

    Parâmetros:
    - candidate: candidato do banco com scores locais
    - ai_cut: corte validado pelo hybrid_parser (pode ser None se sem IA)
    - transcription_quality: qualidade da transcrição (0-1)

    Retorna dict enriquecido com final_score e decision.
    """
    # Score local normalizado (0-1)
    local_raw    = float(candidate.get("combined_score", 0))
    local_norm   = local_raw / 10.0 if local_raw > 1.0 else local_raw

    # Score externo da IA
    if ai_cut:
        external_raw = float(ai_cut.get("viral_score", ai_cut.get("score", 0)))
    else:
        # Sem IA: usa 80% do score local como proxy
        external_raw = local_raw * 0.8

    # Platform fit: média dos fits disponíveis
    plat_scores = [
        float(candidate.get("platform_fit_tiktok",  0)),
        float(candidate.get("platform_fit_reels",   0)),
        float(candidate.get("platform_fit_shorts",  0)),
    ]
    platform_fit = sum(plat_scores) / max(len(plat_scores), 1)

    # Duration fit
    from core.candidate_engine import score_duration_fit
    start    = float(candidate.get("start_time", candidate.get("start", 0)))
    end      = float(candidate.get("end_time",   candidate.get("end",   0)))
    duration = end - start
    duration_fit = score_duration_fit(duration)

    final_score = compute_final_score(
        local_score           = local_norm,
        external_score        = external_raw,
        platform_fit          = platform_fit,
        duration_fit          = duration_fit,
        transcription_quality = transcription_quality,
    )

    decision = classify(final_score)

    result = {**candidate}
    if ai_cut:
        # Mescla dados da IA no resultado
        result["title"]       = ai_cut.get("title",    result.get("title", ""))
        result["hook"]        = ai_cut.get("hook",     result.get("hook",  ""))
        result["archetype"]   = ai_cut.get("archetype", result.get("archetype", ""))
        result["platforms"]   = ai_cut.get("platforms", ["tiktok", "reels", "shorts"])
        result["ai_reason"]   = ai_cut.get("decision",  "")

    result["final_score"] = final_score
    result["decision"]    = decision
    result["local_score"] = round(local_raw, 4)
    result["external_score"] = round(external_raw, 4)

    return result


def decide_all(
    candidates: List[Dict],
    ai_cuts: List[Dict],
    transcription_quality: float = 1.0,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Processa todos os candidatos e retorna três listas:
    - aprovados (final_score ≥ 9.0)
    - rework    (7.0 ≤ final_score < 9.0)
    - descartados

    ai_cuts são casados com candidates por candidate_id.
    """
    # Mapa candidate_id → ai_cut
    ai_map = {c.get("candidate_id", c.get("id")): c for c in ai_cuts}

    aprovados  = []
    rework     = []
    descartados = []

    for cand in candidates:
        cid    = cand.get("id", cand.get("candidate_id"))
        ai_cut = ai_map.get(cid)
        result = decide_cut(cand, ai_cut, transcription_quality)

        if result["decision"] == DECISION_APROVADO:
            aprovados.append(result)
        elif result["decision"] == DECISION_REWORK:
            rework.append(result)
        else:
            descartados.append(result)

    # Ordena por final_score desc
    aprovados.sort(key=lambda x: x["final_score"], reverse=True)
    rework.sort(key=lambda x: x["final_score"], reverse=True)

    return aprovados, rework, descartados


def format_decision_report(
    aprovados: List[Dict],
    rework: List[Dict],
    descartados: List[Dict],
) -> str:
    """Relatório de decisão para exibir na GUI."""
    lines = [
        "═══════════════════════════════════════",
        "    DECISION ENGINE — RELATÓRIO FINAL  ",
        "═══════════════════════════════════════",
        f"  ✅ APROVADOS    : {len(aprovados)}",
        f"  🔄 REWORK       : {len(rework)}",
        f"  ❌ DESCARTADOS  : {len(descartados)}",
        "",
    ]

    if aprovados:
        lines.append("── APROVADOS (render imediato) ──")
        for c in aprovados:
            lines.append(
                f"  [{c['final_score']:.1f}] {c.get('title', 'Sem título')} "
                f"({_fmt(c.get('start_time',0))}→{_fmt(c.get('end_time',0))})"
            )
        lines.append("")

    if rework:
        lines.append("── REWORK (revisão manual) ──")
        for c in rework:
            lines.append(
                f"  [{c['final_score']:.1f}] {c.get('title', 'Sem título')} "
                f"({_fmt(c.get('start_time',0))}→{_fmt(c.get('end_time',0))})"
            )
        lines.append("")

    return "\n".join(lines)


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
