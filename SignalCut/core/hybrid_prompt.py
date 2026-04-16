"""
SignalCut Hybrid — Hybrid Prompt Generator
Gera o contexto ultra-estruturado para a IA externa.

O prompt envia apenas os melhores candidatos locais,
com mapa completo do vídeo para eliminar a "cegueira" da IA.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


# ─── Schema esperado da resposta da IA ───────────────────────────────────────

RESPONSE_SCHEMA = """[
  {
    "candidate_id": <int>,
    "start": <float>,
    "end": <float>,
    "title": "<string — título do corte, max 60 chars>",
    "hook": "<string — frase de gancho, max 100 chars>",
    "archetype": "<string — um dos 10 arquétipos>",
    "score": <float entre 0.0 e 10.0>,
    "platforms": ["tiktok", "reels", "shorts"],
    "reason": "<string — justificativa editorial em 1-2 frases>"
  }
]"""

ARCHETYPES_LIST = [
    "curiosidade", "medo_urgencia", "indignacao", "ganancia",
    "transformacao", "prova_social", "exclusividade", "autoridade",
    "alivio", "empatia"
]


# ─── Builder Principal ────────────────────────────────────────────────────────

def build_hybrid_prompt(
    project_name: str,
    full_transcript: str,
    candidates: List[Dict],
    top_n: int = 8,
    context_hint: str = "",
    niche: str = "",
    platform_focus: str = "tiktok",
) -> str:
    """
    Gera o prompt completo para a IA externa.

    Parâmetros:
    - project_name:    Nome do projeto/vídeo
    - full_transcript: Transcrição completa (para contexto geral)
    - candidates:      Lista de candidatos já pontuados pelo score local
    - top_n:           Quantos candidatos enviar (os melhores por combined_score)
    - context_hint:    Contexto adicional do usuário (nicho, público, objetivo)
    - niche:           Nicho de conteúdo
    - platform_focus:  Plataforma principal
    """
    # Seleciona os melhores candidatos
    top_candidates = _select_top_candidates(candidates, top_n)

    if not top_candidates:
        raise ValueError("Nenhum candidato disponível para o prompt")

    # Monta as seções do prompt
    sections = [
        _section_role(),
        _section_context(project_name, full_transcript, niche, platform_focus, context_hint),
        _section_candidates(top_candidates),
        _section_scoring_criteria(),
        _section_output_instructions(len(top_candidates)),
    ]

    return "\n\n".join(s for s in sections if s.strip())


def build_refinement_prompt(
    original_prompt: str,
    previous_response: str,
    feedback: str,
) -> str:
    """
    Gera prompt de refinamento quando a resposta precisa de ajuste.
    Usado no ciclo de rework (nota 7.0-8.9).
    """
    return f"""Você já analisou este vídeo e forneceu os seguintes cortes:

{previous_response}

FEEDBACK DO EDITOR:
{feedback}

Com base nesse feedback, revise sua análise e retorne um JSON atualizado
seguindo exatamente o mesmo schema anterior.

REGRAS:
- Mantenha os candidate_id originais
- Ajuste apenas os campos que o feedback indica
- Se o feedback pede novos cortes, adicione-os com candidate_id novos
- Retorne APENAS o JSON, sem texto adicional

JSON revisado:"""


# ─── Seções do Prompt ─────────────────────────────────────────────────────────

def _section_role() -> str:
    return """Você é um editor de vídeo sênior especializado em conteúdo viral para plataformas de short-form (TikTok, Instagram Reels, YouTube Shorts).

Sua missão não é criar "Headline Clips" (frases isoladas sem contexto), mas identificar "Scene Clips": trechos com arco narrativo completo, timing natural, viradas (payoffs) e momentos humanos orgânicos que fazem o espectador assistir até o final e compartilhar.

Você tem visão editorial treinada para detectar:
- O momento exato em que o apresentador "entrega" a informação principal
- Transições naturais que criam suspense e retenção
- O equilíbrio entre gancho inicial e resolução satisfatória"""


def _section_context(
    project_name: str,
    full_transcript: str,
    niche: str,
    platform_focus: str,
    context_hint: str,
) -> str:
    # Limita transcrição para não explodir o contexto
    transcript_preview = _truncate_transcript(full_transcript, max_chars=3000)

    niche_line    = f"Nicho: {niche}" if niche else ""
    platform_line = f"Plataforma principal: {platform_focus}"
    hint_line     = f"Contexto adicional: {context_hint}" if context_hint else ""

    metadata = "\n".join(filter(None, [niche_line, platform_line, hint_line]))

    return f"""PROJETO: {project_name}
{metadata}

TRANSCRIÇÃO COMPLETA (para contexto geral):
---
{transcript_preview}
---"""


def _section_candidates(candidates: List[Dict]) -> str:
    lines = ["CANDIDATOS PARA ANÁLISE (pré-selecionados por score local):", ""]

    for i, c in enumerate(candidates):
        cid      = c.get("id", i + 1)
        start    = c.get("start_time", c.get("start", 0))
        end      = c.get("end_time", c.get("end", 0))
        duration = round(end - start, 1)
        text     = c.get("text", "")
        hook     = round(float(c.get("hook_strength",   0)), 2)
        ret      = round(float(c.get("retention_score", 0)), 2)
        moment   = round(float(c.get("moment_strength", 0)), 2)
        combined = round(float(c.get("combined_score",  0)), 2)
        archetype = c.get("archetype", "—")

        lines.append(f"── CANDIDATO #{cid} ──────────────────────────")
        lines.append(f"Tempo: {_fmt_time(start)} → {_fmt_time(end)} ({duration}s)")
        lines.append(f"Arquétipo detectado: {archetype}")
        lines.append(f"Scores locais: Hook={hook} | Retenção={ret} | Momento={moment} | Combined={combined}/10")
        lines.append(f"Texto:")
        lines.append(f'"{text}"')
        lines.append("")

    return "\n".join(lines)


def _section_scoring_criteria() -> str:
    return """CRITÉRIOS DE AVALIAÇÃO EDITORIAL:

1. GANCHO (0-3s): A primeira frase para o scroll imediatamente?
   - Pergunta retórica, dado chocante, imperativo forte = bom gancho
   - "Hoje vou falar sobre..." = gancho fraco

2. RETENÇÃO (3s-80%): O espectador tem motivo para continuar?
   - Tensão não resolvida, promessa implícita, setup de revelação = bom
   - Exposição linear sem conflito = ruim

3. MOMENTO: Existe um ponto de virada, revelação ou punchline?
   - Contraste antes/depois, confissão surpreendente, dado inesperado = sim
   - Conteúdo plano sem clímax = não

4. SHAREABILITY: Alguém vai querer mandar isso pra outra pessoa?
   - Conteúdo universal, provocativo, utilitário ou emocionalmente intenso = alto
   - Específico demais, sem urgência ou sem identificação = baixo

5. PLATAFORMAS: Duração e tom adequados?
   - TikTok/Reels: 15-60s, intenso, rápido
   - Shorts: 15-60s, informativo, objetivo
   - Faixa ideal: 18-35s"""


def _section_output_instructions(n_candidates: int) -> str:
    return f"""INSTRUÇÕES DE OUTPUT:

Analise os {n_candidates} candidatos acima e retorne um JSON com os que merecem virar cortes virais.

REGRAS OBRIGATÓRIAS:
- Retorne APENAS o JSON puro, sem markdown, sem texto antes ou depois
- Inclua apenas candidatos com potencial real (score ≥ 7.0)
- Máximo de {min(n_candidates, 6)} cortes no retorno
- Use os candidate_id exatamente como fornecidos
- start e end devem ser os mesmos do candidato (não invente novos)
- hook deve ser uma frase concreta extraída ou adaptada do texto do candidato
- reason deve ser específica, não genérica ("gancho forte com pergunta retórica" não "bom conteúdo")

ARQUÉTIPOS VÁLIDOS: {", ".join(ARCHETYPES_LIST)}

SCHEMA EXATO:
{RESPONSE_SCHEMA}

JSON:"""


# ─── Utils ────────────────────────────────────────────────────────────────────

def _select_top_candidates(candidates: List[Dict], top_n: int) -> List[Dict]:
    """Seleciona os N melhores candidatos por combined_score."""
    valid = [c for c in candidates if float(c.get("combined_score", 0)) > 0]
    sorted_cands = sorted(valid, key=lambda c: float(c.get("combined_score", 0)), reverse=True)
    return sorted_cands[:top_n]


def _truncate_transcript(text: str, max_chars: int = 3000) -> str:
    """
    Trunca a transcrição inteligentemente:
    - Mantém o início (gancho) e o final (conclusão)
    - Substitui o meio por "[...]"
    """
    if len(text) <= max_chars:
        return text

    half = max_chars // 2
    start_part = text[:half]
    end_part   = text[-half:]

    # Quebra em palavra limpa
    last_space_start = start_part.rfind(" ")
    first_space_end  = end_part.find(" ")

    if last_space_start > 0:
        start_part = start_part[:last_space_start]
    if first_space_end > 0:
        end_part = end_part[first_space_end + 1:]

    return f"{start_part}\n\n[... trecho omitido para reduzir contexto ...]\n\n{end_part}"


def _fmt_time(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
