"""
SignalCut Hybrid — Learning Engine
Fecha o loop de aprendizado: performance real → ajuste de pesos.

Quando um corte performa bem/mal nas plataformas,
o motor ajusta os pesos dos arquétipos em scoring.yaml.
"""

import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


_SCORING_PATH = Path(__file__).parent.parent / "data" / "scoring.yaml"


# ─── Métricas de Performance ─────────────────────────────────────────────────

def compute_engagement_rate(views: int, likes: int, shares: int, comments: int) -> float:
    """
    Taxa de engajamento ponderada.
    Shares têm peso maior (indicam conteúdo viral real).
    """
    if views == 0:
        return 0.0
    weighted = (likes * 1.0) + (shares * 3.0) + (comments * 2.0)
    return round(min(weighted / views, 1.0), 6)


def compute_viral_index(views: int, shares: int, duration_hours: float) -> float:
    """
    Índice de viralidade: taxa de crescimento de views/hora normalizada.
    """
    if duration_hours <= 0 or views == 0:
        return 0.0
    views_per_hour = views / duration_hours
    share_rate = shares / max(views, 1)
    # Log para suavizar outliers
    raw = math.log(1 + views_per_hour) * (1 + share_rate * 10)
    return round(min(raw / 10.0, 1.0), 6)


# ─── Coleta de Performance ────────────────────────────────────────────────────

def record_performance(
    db_path: str,
    cut_id: int,
    platform: str,
    views: int,
    likes: int = 0,
    shares: int = 0,
    comments: int = 0,
    posted_at: Optional[str] = None,
) -> Dict:
    """
    Registra dados de performance no banco.
    Retorna métricas calculadas.
    """
    import sqlite3
    posted_at = posted_at or datetime.now().isoformat()

    engagement = compute_engagement_rate(views, likes, shares, comments)

    duration_hours = 24.0  # default: assume 24h de vida
    if posted_at:
        try:
            posted_dt = datetime.fromisoformat(posted_at)
            now_dt    = datetime.now()
            duration_hours = max((now_dt - posted_dt).total_seconds() / 3600, 1.0)
        except Exception:
            pass

    viral_index = compute_viral_index(views, shares, duration_hours)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO performances
               (cut_id, platform, views, likes, shares, comments, posted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cut_id, platform, views, likes, shares, comments, posted_at)
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "engagement_rate": engagement,
        "viral_index":     viral_index,
        "views":           views,
        "platform":        platform,
    }


# ─── Análise de Performance por Arquétipo ─────────────────────────────────────

def analyze_archetype_performance(
    db_path: str,
    min_samples: int = 3,
) -> Dict[str, Dict]:
    """
    Analisa performance real por arquétipo.
    Retorna dict com métricas médias por arquétipo.
    Só processa arquétipos com >= min_samples cortes.
    """
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Junta cuts com performances
        rows = conn.execute("""
            SELECT
                c.archetype,
                AVG(p.views)    AS avg_views,
                AVG(p.likes)    AS avg_likes,
                AVG(p.shares)   AS avg_shares,
                AVG(p.comments) AS avg_comments,
                COUNT(*)        AS n_samples
            FROM cuts c
            JOIN performances p ON p.cut_id = c.id
            WHERE c.archetype IS NOT NULL AND c.archetype != ''
            GROUP BY c.archetype
            HAVING COUNT(*) >= ?
        """, (min_samples,)).fetchall()
    finally:
        conn.close()

    results = {}
    for row in rows:
        arch = row["archetype"]
        avg_views    = float(row["avg_views"]    or 0)
        avg_likes    = float(row["avg_likes"]    or 0)
        avg_shares   = float(row["avg_shares"]   or 0)
        avg_comments = float(row["avg_comments"] or 0)
        n            = int(row["n_samples"])

        engagement = compute_engagement_rate(
            int(avg_views), int(avg_likes), int(avg_shares), int(avg_comments)
        )

        results[arch] = {
            "avg_views":       round(avg_views, 1),
            "avg_engagement":  engagement,
            "n_samples":       n,
        }

    return results


# ─── Ajuste de Pesos ──────────────────────────────────────────────────────────

def update_archetype_weights(
    db_path: str,
    dry_run: bool = False,
) -> Tuple[Dict, List[str]]:
    """
    Atualiza pesos dos arquétipos em scoring.yaml baseado na performance real.

    Algoritmo:
    1. Calcula engagement médio por arquétipo
    2. Normaliza em relação à média global
    3. Ajusta peso = peso_atual * (1 + taxa_ajuste * delta)
    4. Clipa entre 0.10 e 0.50
    5. Salva no scoring.yaml

    dry_run=True: calcula mas não salva (para preview).

    Retorna (novos_pesos, log_mensagens).
    """
    perf = analyze_archetype_performance(db_path)
    if not perf:
        return {}, ["Dados insuficientes para ajuste de pesos (mínimo 3 amostras por arquétipo)"]

    log = []

    # Média global de engajamento
    global_avg = sum(p["avg_engagement"] for p in perf.values()) / len(perf)
    if global_avg == 0:
        return {}, ["Engajamento médio zero — sem dados reais ainda"]

    # Carrega configuração atual
    with open(_SCORING_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    archetypes = config.get("archetypes", {})
    new_weights = {}
    LEARNING_RATE = 0.15  # ajuste máximo de 15% por ciclo

    for arch_name, arch_data in archetypes.items():
        current_weight = float(arch_data.get("weight", 0.25))

        if arch_name not in perf:
            new_weights[arch_name] = current_weight
            continue

        arch_engagement = perf[arch_name]["avg_engagement"]
        n_samples       = perf[arch_name]["n_samples"]

        # Delta: quão melhor/pior que a média
        delta = (arch_engagement - global_avg) / max(global_avg, 0.001)
        # Ajuste conservador
        adjustment = current_weight * LEARNING_RATE * delta
        # Fator de confiança: mais amostras = mais confiança no ajuste
        confidence = min(n_samples / 20.0, 1.0)
        new_weight = current_weight + (adjustment * confidence)
        # Clipa entre limites razoáveis
        new_weight = round(max(0.10, min(0.50, new_weight)), 4)

        new_weights[arch_name] = new_weight

        if abs(new_weight - current_weight) > 0.001:
            direction = "↑" if new_weight > current_weight else "↓"
            log.append(
                f"{direction} {arch_name}: {current_weight:.3f} → {new_weight:.3f} "
                f"(engagement: {arch_engagement:.4f}, samples: {n_samples})"
            )

    if not dry_run and log:
        # Atualiza o YAML
        for arch_name, weight in new_weights.items():
            if arch_name in archetypes:
                archetypes[arch_name]["weight"] = weight

        config["archetypes"]   = archetypes
        config["last_updated"] = datetime.now().isoformat()

        with open(_SCORING_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        log.append(f"✅ scoring.yaml atualizado — {len(log)} arquétipos ajustados")
    elif dry_run:
        log.append("ℹ️  dry_run=True — pesos calculados mas não salvos")
    else:
        log.append("ℹ️  Nenhum ajuste necessário (pesos já otimizados)")

    return new_weights, log


# ─── Relatório de Aprendizado ─────────────────────────────────────────────────

def generate_learning_report(db_path: str) -> str:
    """Relatório de performance para exibir na GUI."""
    perf = analyze_archetype_performance(db_path, min_samples=1)

    lines = [
        "═══════════════════════════════════════",
        "    LEARNING ENGINE — PERFORMANCE      ",
        "═══════════════════════════════════════",
    ]

    if not perf:
        lines.append("  Sem dados de performance ainda.")
        lines.append("  Registre resultados das plataformas para ativar o aprendizado.")
        return "\n".join(lines)

    sorted_archs = sorted(perf.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)

    lines.append(f"  {'Arquétipo':<20} {'Eng.Rate':>10} {'Views Avg':>12} {'Amostras':>10}")
    lines.append("  " + "─" * 55)

    for arch, data in sorted_archs:
        lines.append(
            f"  {arch:<20} "
            f"{data['avg_engagement']:>9.4f} "
            f"{data['avg_views']:>12.0f} "
            f"{data['n_samples']:>10}"
        )

    lines.append("")
    lines.append("  Use 'Atualizar Pesos' para incorporar esses dados ao scoring.")
    return "\n".join(lines)
