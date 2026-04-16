"""
SignalCut Hybrid — Output Manager
Gera o pacote social completo para cada corte aprovado.

Para cada corte entrega:
- Arquivo de vídeo renderizado (via cut_engine)
- Texto de legenda com hashtags por plataforma
- Prompt de thumbnail para IA de imagem
- Relatório de proteção aplicada
- Metadados JSON para a plataforma
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable


# ─── Templates de Legenda ─────────────────────────────────────────────────────

CAPTION_TEMPLATES = {
    "curiosidade": {
        "opener":  "Você sabia que {hook}",
        "cta":     "💡 Salva pra não esquecer",
        "hashtags_base": ["#curiosidade", "#vocesabia", "#dicasdedia"],
    },
    "medo_urgencia": {
        "opener":  "⚠️ ATENÇÃO: {hook}",
        "cta":     "🚨 Compartilha com quem precisa saber",
        "hashtags_base": ["#urgente", "#cuidado", "#alertadodia"],
    },
    "indignacao": {
        "opener":  "Isso precisa parar: {hook}",
        "cta":     "🔥 Comenta o que você acha",
        "hashtags_base": ["#verdade", "#absurdo", "#precisamosfalarsobre"],
    },
    "ganancia": {
        "opener":  "💰 {hook}",
        "cta":     "💸 Salva essa dica",
        "hashtags_base": ["#dinheiro", "#financas", "#investimento"],
    },
    "transformacao": {
        "opener":  "Isso mudou minha vida: {hook}",
        "cta":     "🦋 Marca quem precisa dessa transformação",
        "hashtags_base": ["#transformacao", "#mudanca", "#evolucao"],
    },
    "prova_social": {
        "opener":  "Milhares de pessoas já descobriram: {hook}",
        "cta":     "📢 Compartilha com seus amigos",
        "hashtags_base": ["#viral", "#tendencia", "#todosmundo"],
    },
    "exclusividade": {
        "opener":  "🔒 Conteúdo exclusivo: {hook}",
        "cta":     "⭐ Segue pra mais conteúdo assim",
        "hashtags_base": ["#exclusivo", "#segredo", "#metodo"],
    },
    "autoridade": {
        "opener":  "A ciência comprova: {hook}",
        "cta":     "📚 Salva e aprende mais",
        "hashtags_base": ["#ciencia", "#especialista", "#comprovado"],
    },
    "alivio": {
        "opener":  "Finalmente uma solução: {hook}",
        "cta":     "✅ Salva pra quando precisar",
        "hashtags_base": ["#solucao", "#finalmente", "#funcionou"],
    },
    "empatia": {
        "opener":  "Você não está sozinho: {hook}",
        "cta":     "❤️ Marca quem precisa ouvir isso",
        "hashtags_base": ["#empatia", "#vocenonesta", "#apoio"],
    },
}

PLATFORM_HASHTAG_RULES = {
    "tiktok":    {"max_tags": 5,  "include_fyp": True},
    "reels":     {"max_tags": 8,  "include_fyp": False},
    "shorts":    {"max_tags": 3,  "include_fyp": False},
}

FYP_TAGS = ["#fyp", "#foryou", "#foryoupage", "#viral"]


# ─── Output Manager ──────────────────────────────────────────────────────────

class OutputManager:
    def __init__(
        self,
        output_dir: str,
        project_id: int,
        project_name: str,
        niche: str = "",
        progress_cb: Optional[Callable] = None,
    ):
        self.output_dir   = Path(output_dir)
        self.project_id   = project_id
        self.project_name = project_name
        self.niche        = niche
        self.log          = progress_cb or print
        self._ensure_dirs()

    def _ensure_dirs(self):
        for sub in ["tiktok", "reels", "shorts", "metadata", "thumbnails"]:
            (self.output_dir / sub).mkdir(parents=True, exist_ok=True)

    # ─── Geração do Pacote ────────────────────────────────────────────────────

    def generate_package(
        self,
        cut: Dict,
        video_path: str,
        segments: List[Dict],
        ace_level: str = "basic",
        use_vaapi: bool = True,
    ) -> Dict:
        """
        Gera pacote completo para um corte.

        Retorna dict com paths de todos os arquivos gerados.
        """
        self.log(f"\n📦 Gerando pacote: {cut.get('title', 'Corte')}")

        package = {
            "cut_id":       cut.get("id", cut.get("candidate_id")),
            "title":        cut.get("title", ""),
            "archetype":    cut.get("archetype", ""),
            "final_score":  cut.get("final_score", 0),
            "platforms":    cut.get("platforms", ["tiktok", "reels", "shorts"]),
            "video_paths":  {},
            "captions":     {},
            "metadata":     {},
            "thumbnail_prompt": "",
            "generated_at": datetime.now().isoformat(),
        }

        # 1. Renderiza vídeos
        try:
            from core.cut_engine import render_cut
            video_paths = render_cut(
                video_path   = video_path,
                cut          = cut,
                segments     = segments,
                output_dir   = str(self.output_dir),
                project_id   = str(self.project_id),
                ace_level    = ace_level,
                use_vaapi    = use_vaapi,
                progress_cb  = self.log,
            )
            package["video_paths"] = video_paths
            self.log(f"  ✅ Vídeos renderizados: {list(video_paths.keys())}")
        except Exception as e:
            self.log(f"  ❌ Erro no render: {e}")
            package["render_error"] = str(e)

        # 2. Gera legendas para cada plataforma
        for platform in package["platforms"]:
            caption = self.generate_caption(cut, platform, self.niche)
            package["captions"][platform] = caption

        # 3. Gera metadados JSON
        package["metadata"] = self._generate_metadata(cut)

        # 4. Gera prompt de thumbnail
        package["thumbnail_prompt"] = self.generate_thumbnail_prompt(cut)

        # 5. Salva pacote em JSON
        package_path = self.output_dir / "metadata" / f"package_{package['cut_id']}.json"
        with open(package_path, "w", encoding="utf-8") as f:
            json.dump(package, f, ensure_ascii=False, indent=2)

        self.log(f"  📋 Pacote salvo: {package_path.name}")
        return package

    def generate_all(
        self,
        cuts: List[Dict],
        video_path: str,
        segments: List[Dict],
        ace_level: str = "basic",
        use_vaapi: bool = True,
    ) -> List[Dict]:
        """Processa todos os cortes aprovados."""
        packages = []
        total = len(cuts)
        for i, cut in enumerate(cuts):
            self.log(f"\n[{i+1}/{total}] {cut.get('title', 'Sem título')}")
            pkg = self.generate_package(cut, video_path, segments, ace_level, use_vaapi)
            packages.append(pkg)
        return packages

    # ─── Geração de Legenda ───────────────────────────────────────────────────

    def generate_caption(
        self,
        cut: Dict,
        platform: str,
        niche: str = "",
    ) -> str:
        """
        Gera legenda otimizada para a plataforma.

        Estrutura:
        1. Opener com hook
        2. Corpo (2-3 linhas do conteúdo)
        3. CTA
        4. Hashtags
        """
        archetype = cut.get("archetype", "curiosidade")
        hook      = cut.get("hook", cut.get("title", ""))
        template  = CAPTION_TEMPLATES.get(archetype, CAPTION_TEMPLATES["curiosidade"])

        # Opener
        opener = template["opener"].format(hook=hook)

        # Corpo breve baseado no texto do corte
        text  = cut.get("text", "")
        corpo = _extract_caption_body(text, max_chars=200)

        # CTA
        cta = template["cta"]

        # Hashtags
        hashtags = self._build_hashtags(archetype, platform, niche)

        lines = [opener]
        if corpo:
            lines.append("")
            lines.append(corpo)
        lines.append("")
        lines.append(cta)
        lines.append("")
        lines.append(hashtags)

        return "\n".join(lines)

    def _build_hashtags(self, archetype: str, platform: str, niche: str) -> str:
        rules = PLATFORM_HASHTAG_RULES.get(platform, {"max_tags": 5, "include_fyp": False})
        max_tags = rules["max_tags"]

        tags = list(CAPTION_TEMPLATES.get(archetype, {}).get("hashtags_base", []))

        # Tags de nicho
        if niche:
            niche_tag = "#" + re.sub(r'[^a-zA-ZáéíóúãõçÁÉÍÓÚÃÕÇ]', '', niche.replace(" ", ""))
            if niche_tag not in tags:
                tags.insert(0, niche_tag.lower())

        # FYP tags para TikTok
        if rules.get("include_fyp"):
            tags = FYP_TAGS[:2] + tags

        # Limita
        tags = tags[:max_tags]
        return " ".join(tags)

    # ─── Thumbnail Prompt ─────────────────────────────────────────────────────

    def generate_thumbnail_prompt(self, cut: Dict) -> str:
        """
        Gera prompt para IA de geração de imagem (Midjourney, DALL-E, etc).
        """
        archetype = cut.get("archetype", "curiosidade")
        title     = cut.get("title", "")
        hook      = cut.get("hook", "")

        style_map = {
            "curiosidade":   "mysterious dark background, glowing question mark, cinematic",
            "medo_urgencia": "red warning atmosphere, dramatic lighting, urgent feeling",
            "indignacao":    "bold red and black, confrontational energy, raw emotion",
            "ganancia":      "gold and green tones, abundance symbols, aspirational",
            "transformacao": "split screen before/after, butterfly motif, inspiring",
            "prova_social":  "crowd energy, social proof, trending atmosphere",
            "exclusividade": "premium dark aesthetic, VIP feeling, mysterious",
            "autoridade":    "clean professional, trustworthy, credible tone",
            "alivio":        "warm light, calm after storm, relief feeling",
            "empatia":       "warm human connection, soft lighting, relatable",
        }
        style = style_map.get(archetype, "cinematic, high contrast, viral content")

        return (
            f"YouTube thumbnail style, {style}, "
            f"bold text overlay: '{title[:30]}', "
            f"high contrast, eye-catching, professional viral content, "
            f"16:9 aspect ratio, 1280x720, no watermarks"
        )

    # ─── Metadados ────────────────────────────────────────────────────────────

    def _generate_metadata(self, cut: Dict) -> Dict:
        return {
            "project_id":   self.project_id,
            "project_name": self.project_name,
            "title":        cut.get("title", ""),
            "hook":         cut.get("hook",  ""),
            "archetype":    cut.get("archetype", ""),
            "final_score":  cut.get("final_score", 0),
            "local_score":  cut.get("local_score",  0),
            "external_score": cut.get("external_score", 0),
            "duration":     round(
                float(cut.get("end_time", cut.get("end", 0))) -
                float(cut.get("start_time", cut.get("start", 0))),
                2
            ),
            "platforms":    cut.get("platforms", []),
            "ai_reason":    cut.get("ai_reason", cut.get("decision", "")),
            "generated_at": datetime.now().isoformat(),
        }

    # ─── Relatório ────────────────────────────────────────────────────────────

    def generate_summary_report(self, packages: List[Dict]) -> str:
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║       SIGNALCUT — PACOTE SOCIAL GERADO           ║",
            "╚══════════════════════════════════════════════════╝",
            f"  Projeto  : {self.project_name}",
            f"  Cortes   : {len(packages)}",
            f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "",
        ]
        for i, pkg in enumerate(packages, 1):
            lines.append(f"── Corte {i}: {pkg['title']} ──")
            lines.append(f"   Score   : {pkg['final_score']:.1f}/10")
            lines.append(f"   Arch    : {pkg['archetype']}")
            for plat, path in pkg.get("video_paths", {}).items():
                size = os.path.getsize(path) / (1024*1024) if path and os.path.exists(path) else 0
                lines.append(f"   {plat:8}: {os.path.basename(path)} ({size:.1f}MB)")
            lines.append("")
        return "\n".join(lines)


# ─── Utils ────────────────────────────────────────────────────────────────────

def _extract_caption_body(text: str, max_chars: int = 200) -> str:
    """Extrai 2-3 frases do meio do texto para o corpo da legenda."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

    if not sentences:
        return ""

    # Pega do meio (não o início — esse é o hook)
    start = max(1, len(sentences) // 4)
    end   = min(len(sentences), start + 2)
    body  = " ".join(sentences[start:end])

    if len(body) > max_chars:
        body = body[:max_chars].rsplit(" ", 1)[0] + "..."

    return body
