"""
SignalCut Hybrid — Hybrid Parser
Firewall de dados: valida e sanitiza respostas da IA externa.
Rejeita qualquer JSON malformado antes de tocar no banco.

Regra central: dados sujos nunca chegam à tabela `cuts`.
"""

import json
import re
from typing import Dict, List, Optional, Tuple


# ─── Schema de Validação ─────────────────────────────────────────────────────

VALID_ARCHETYPES = {
    "curiosidade", "medo_urgencia", "indignacao", "ganancia",
    "transformacao", "prova_social", "exclusividade", "autoridade",
    "alivio", "empatia",
    # aliases em inglês (IA às vezes responde em inglês)
    "curiosity", "fear", "anger", "greed", "transformation",
    "social_proof", "exclusivity", "authority", "relief", "empathy",
}

VALID_PLATFORMS = {"tiktok", "reels", "shorts", "youtube"}

ARCHETYPE_ALIASES = {
    "curiosity":     "curiosidade",
    "fear":          "medo_urgencia",
    "urgency":       "medo_urgencia",
    "anger":         "indignacao",
    "greed":         "ganancia",
    "transformation":"transformacao",
    "social_proof":  "prova_social",
    "exclusivity":   "exclusividade",
    "authority":     "autoridade",
    "relief":        "alivio",
    "empathy":       "empatia",
}


# ─── Parser Principal ─────────────────────────────────────────────────────────

def parse_ai_response(
    raw_response: str,
    known_candidates: List[Dict],
    strict: bool = False,
) -> Tuple[List[Dict], List[str]]:
    """
    Parseia e valida a resposta JSON da IA externa.

    Parâmetros:
    - raw_response:      Texto bruto retornado pela IA
    - known_candidates:  Candidatos locais (para validar candidate_id e tempos)
    - strict:            Se True, rejeita qualquer desvio do schema

    Retorna:
    - (cuts_válidos, erros)
      cuts_válidos: lista de dicts prontos para inserir na tabela `cuts`
      erros: lista de strings descrevendo problemas encontrados
    """
    errors: List[str] = []

    # 1. Extrai JSON do texto (IA às vezes adiciona markdown ou texto extra)
    json_str, extraction_error = _extract_json(raw_response)
    if extraction_error:
        errors.append(f"Extração JSON: {extraction_error}")
        if strict:
            return [], errors

    # 2. Parse do JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        errors.append(f"JSON inválido: {e}")
        return [], errors

    # 3. Garante que é uma lista
    if isinstance(data, dict):
        # IA às vezes retorna {"cuts": [...]} ou {"results": [...]}
        for key in ["cuts", "results", "cortes", "clips"]:
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            errors.append("JSON é um objeto mas não contém lista de cortes reconhecível")
            return [], errors

    if not isinstance(data, list):
        errors.append(f"Esperado lista, recebido: {type(data).__name__}")
        return [], errors

    # 4. Valida cada item
    candidate_map = {c.get("id", c.get("candidate_id")): c for c in known_candidates}
    validated_cuts: List[Dict] = []

    for i, item in enumerate(data):
        cut, item_errors = _validate_cut(item, i, candidate_map, strict)
        if item_errors:
            errors.extend([f"Item #{i+1}: {e}" for e in item_errors])
        if cut:
            validated_cuts.append(cut)

    return validated_cuts, errors


def validate_response_schema(raw_response: str) -> bool:
    """Verifica rapidamente se a resposta parece válida (sem processar completo)."""
    json_str, _ = _extract_json(raw_response)
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), data)
        return isinstance(data, list) and len(data) > 0
    except Exception:
        return False


# ─── Validação de Item ────────────────────────────────────────────────────────

def _validate_cut(
    item: Dict,
    index: int,
    candidate_map: Dict,
    strict: bool,
) -> Tuple[Optional[Dict], List[str]]:
    """
    Valida um item de corte individual.
    Retorna (cut_validado, erros).
    """
    errors: List[str] = []

    if not isinstance(item, dict):
        return None, [f"Item não é um objeto: {type(item).__name__}"]

    # ── candidate_id ──
    cid = item.get("candidate_id") or item.get("id")
    if cid is None:
        if strict:
            return None, ["candidate_id ausente"]
        cid = index + 1
        errors.append(f"candidate_id ausente — assumindo {cid}")
    try:
        cid = int(cid)
    except (ValueError, TypeError):
        return None, [f"candidate_id inválido: {cid!r}"]

    # ── start / end ──
    start = _parse_float(item.get("start") or item.get("start_time"))
    end   = _parse_float(item.get("end")   or item.get("end_time"))

    if start is None or end is None:
        # Tenta recuperar do candidato local
        local = candidate_map.get(cid)
        if local:
            start = start or float(local.get("start_time", local.get("start", 0)))
            end   = end   or float(local.get("end_time",   local.get("end",   0)))
            errors.append("start/end ausentes — recuperados do candidato local")
        else:
            return None, ["start/end ausentes e candidato local não encontrado"]

    if end <= start:
        return None, [f"end ({end}) deve ser maior que start ({start})"]

    if end - start < 5.0:
        return None, [f"Duração muito curta: {end - start:.1f}s"]

    # Valida contra o candidato local (evita a IA inventar tempos)
    local = candidate_map.get(cid)
    if local and not strict:
        local_start = float(local.get("start_time", local.get("start", 0)))
        local_end   = float(local.get("end_time",   local.get("end",   0)))
        # Tolera até 3s de diferença
        if abs(start - local_start) > 3.0 or abs(end - local_end) > 3.0:
            errors.append(f"Tempos divergem do candidato local por mais de 3s — usando local")
            start = local_start
            end   = local_end

    # ── title ──
    title = str(item.get("title") or "").strip()
    if not title:
        title = f"Corte {cid}"
        errors.append("title ausente — usando padrão")
    title = title[:80]  # trunca se muito longo

    # ── hook ──
    hook = str(item.get("hook") or "").strip()
    if not hook:
        hook = ""
        if strict:
            errors.append("hook ausente")
    hook = hook[:150]

    # ── archetype ──
    archetype = str(item.get("archetype") or "").lower().strip()
    archetype = ARCHETYPE_ALIASES.get(archetype, archetype)
    if archetype not in VALID_ARCHETYPES:
        errors.append(f"Arquétipo desconhecido: {archetype!r} — usando 'curiosidade'")
        archetype = "curiosidade"

    # ── score ──
    score = _parse_float(item.get("score") or item.get("viral_score"))
    if score is None:
        score = 7.0
        errors.append("score ausente — assumindo 7.0")
    score = max(0.0, min(10.0, float(score)))

    # ── platforms ──
    raw_platforms = item.get("platforms") or []
    if isinstance(raw_platforms, str):
        raw_platforms = [p.strip() for p in raw_platforms.split(",")]
    platforms = [p.lower().strip() for p in raw_platforms if p.lower().strip() in VALID_PLATFORMS]
    if not platforms:
        platforms = ["tiktok", "reels", "shorts"]
        errors.append("platforms ausente ou inválido — usando todos")

    # ── reason ──
    reason = str(item.get("reason") or item.get("justificativa") or "").strip()
    reason = reason[:500]

    # ── Constrói cut validado ──
    cut = {
        "candidate_id": cid,
        "start_time":   round(start, 3),
        "end_time":     round(end,   3),
        "duration":     round(end - start, 3),
        "title":        title,
        "hook":         hook,
        "archetype":    archetype,
        "viral_score":  round(score, 2),
        "platforms":    platforms,
        "decision":     reason,
    }

    return cut, errors


# ─── Extração de JSON ─────────────────────────────────────────────────────────

def _extract_json(text: str) -> Tuple[str, Optional[str]]:
    """
    Extrai JSON de uma resposta que pode conter texto extra.

    Estratégias:
    1. Blocos ```json ... ```
    2. Primeiro [ ... ] encontrado
    3. Primeiro { ... } encontrado
    4. Texto completo como fallback
    """
    text = text.strip()

    # 1. Markdown code block
    md_match = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if md_match:
        return md_match.group(1).strip(), None

    # 2. Array JSON
    arr_match = re.search(r'(\[[\s\S]+\])', text)
    if arr_match:
        return arr_match.group(1).strip(), None

    # 3. Objeto JSON
    obj_match = re.search(r'(\{[\s\S]+\})', text)
    if obj_match:
        return obj_match.group(1).strip(), None

    # 4. Fallback — texto completo
    return text, "Nenhuma estrutura JSON clara detectada — usando texto completo"


# ─── Utils ────────────────────────────────────────────────────────────────────

def _parse_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def format_parse_report(cuts: List[Dict], errors: List[str]) -> str:
    """Formata relatório de parsing para exibir na GUI."""
    lines = [f"✅ {len(cuts)} cortes validados"]
    if errors:
        lines.append(f"⚠️  {len(errors)} avisos:")
        for e in errors[:10]:  # máximo 10 erros na GUI
            lines.append(f"  • {e}")
    return "\n".join(lines)
