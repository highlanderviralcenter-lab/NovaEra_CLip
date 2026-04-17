import re
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Nicho(Enum):
    INVESTIMENTOS = "investimentos"
    FITNESS = "fitness"
    TECNOLOGIA = "tecnologia"
    RELACIONAMENTOS = "relacionamentos"
    EMPREENDEDORISMO = "empreendedorismo"
    GERAL = "geral"


class Archetype(Enum):
    DESPERTAR = "despertar"
    TENSAO = "tensao"
    CONFRONTO = "confronto"
    VIRADA = "virada"
    REVELACAO = "revelacao"
    JUSTO_ENGOLIDO = "justo_engolido"
    TRANSFORMACAO = "transformacao"
    RESOLUCAO = "resolucao"
    IMPACTO = "impacto"
    ENCERRAMENTO = "encerramento"


class Platform(Enum):
    TIKTOK = "tiktok"
    REELS = "reels"
    SHORTS = "shorts"


@dataclass
class Cut:
    id: str
    text: str
    duration: float
    start_time: float = 0.0
    viral_score: float = 0.0
    platform: Optional[Platform] = None
    hooks: List[str] = field(default_factory=list)
    archetype: Optional[Archetype] = None


class ViralEngine:
    """Motor autônomo de análise viral."""

    NICHO_KEYWORDS = {
        Nicho.INVESTIMENTOS: ["dinheiro", "investir", "bitcoin", "renda", "juros", "bolsa", "lucro"],
        Nicho.FITNESS: ["academia", "treino", "dieta", "musculação", "emagrecer", "hipertrofia"],
        Nicho.TECNOLOGIA: ["ia", "inteligência artificial", "software", "app", "algoritmo", "dados"],
        Nicho.RELACIONAMENTOS: ["namoro", "amor", "traição", "ciúmes", "casamento", "crush"],
        Nicho.EMPREENDEDORISMO: ["negócio", "startup", "vendas", "cliente", "produto", "faturamento"],
    }

    HOOK_TEMPLATES = {
        Archetype.DESPERTAR: [
            "Você não vai acreditar no que descobri sobre {tema}...",
            "Pare tudo. Isso sobre {tema} muda tudo.",
            "Ninguém te contou isso sobre {tema}.",
        ],
        Archetype.TENSAO: [
            "O que vou te contar sobre {tema} pode te irritar...",
            "Tem algo errado em {tema} e eu vou mostrar.",
            "Você precisa saber disso antes de continuar com {tema}.",
        ],
        Archetype.CONFRONTO: [
            "Discordo 100% do que falam sobre {tema}.",
            "A maior mentira sobre {tema} é essa.",
            "Se você acredita nisso sobre {tema}, está errado.",
        ],
        Archetype.VIRADA: [
            "Achei que entendia {tema} até descobrir isso...",
            "A virada sobre {tema} que ninguém esperava.",
            "Foi aqui que tudo mudou em {tema}.",
        ],
        Archetype.REVELACAO: [
            "O segredo sobre {tema} que escondem de você.",
            "A verdade sobre {tema}, sem filtro.",
            "Revelação: o ponto central de {tema}.",
        ],
        Archetype.JUSTO_ENGOLIDO: [
            "Fui enganado sobre {tema} por anos.",
            "Como perdi tempo acreditando nisso sobre {tema}.",
            "A mentira de {tema} que me custou caro.",
        ],
        Archetype.TRANSFORMACAO: [
            "Como {tema} transformou minha realidade.",
            "Antes e depois de aplicar isso em {tema}.",
            "De travado para consistente com {tema}.",
        ],
        Archetype.RESOLUCAO: [
            "Resolvi meu maior problema com {tema} assim.",
            "A solução direta para destravar {tema}.",
            "Chega de erro em {tema}: faça isso.",
        ],
        Archetype.IMPACTO: [
            "Isso sobre {tema} vai te chocar.",
            "Números fortes sobre {tema} que ninguém mostra.",
            "A realidade dura de {tema}.",
        ],
        Archetype.ENCERRAMENTO: [
            "E foi assim que {tema} fechou esse ciclo.",
            "A lição final de {tema}.",
            "Resultado final da jornada em {tema}.",
        ],
    }

    HORARIOS_OTIMOS = {
        Platform.TIKTOK: ["08:00", "12:00", "19:00", "21:00"],
        Platform.REELS: ["09:00", "13:00", "18:00", "20:00"],
        Platform.SHORTS: ["10:00", "14:00", "16:00", "20:00"],
    }

    PALAVRAS_GANCHO = ["segredo", "revelação", "chocante", "mentira", "verdade", "alerta"]
    PALAVRAS_SHARE = ["inacreditável", "revoltante", "inspirador", "transformador", "crucial"]
    PALAVRAS_COMENTARIO = ["discordo", "concorda", "errado", "certo", "o que acham", "comentem"]

    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-záéíóúãõâêîôûàèìòùç]{3,}\b", (text or "").lower())
        stopwords = {
            "que", "como", "para", "mas", "por", "são", "esse", "essa",
            "todo", "toda", "muito", "mais", "quando", "onde", "assim",
            "depois", "antes", "agora", "aqui",
        }
        return [w for w in words if w not in stopwords]

    def detect_nicho(self, transcription: str) -> Nicho:
        text_lower = (transcription or "").lower()
        if not text_lower.strip():
            return Nicho.GERAL

        scores = {}
        for nicho, keywords in self.NICHO_KEYWORDS.items():
            scores[nicho] = sum(1 for kw in keywords if kw in text_lower)

        top = max(scores, key=scores.get) if scores else Nicho.GERAL
        return top if scores.get(top, 0) > 0 else Nicho.GERAL

    def analyze_audience(self, transcription: str) -> Dict[str, Any]:
        nicho = self.detect_nicho(transcription)
        idade_map = {
            Nicho.INVESTIMENTOS: {"min": 25, "max": 45, "media": 32},
            Nicho.FITNESS: {"min": 18, "max": 35, "media": 26},
            Nicho.TECNOLOGIA: {"min": 18, "max": 40, "media": 28},
            Nicho.RELACIONAMENTOS: {"min": 18, "max": 35, "media": 24},
            Nicho.EMPREENDEDORISMO: {"min": 22, "max": 45, "media": 30},
            Nicho.GERAL: {"min": 18, "max": 45, "media": 28},
        }
        idade = idade_map[nicho]
        return {
            "nicho_detectado": nicho.value,
            "demografia": {
                "idade_media": idade["media"],
                "faixa_etaria": f"{idade['min']}-{idade['max']} anos",
            },
            "comportamento": {
                "horarios_otimos_postagem": {
                    "tiktok": self.HORARIOS_OTIMOS[Platform.TIKTOK],
                    "reels": self.HORARIOS_OTIMOS[Platform.REELS],
                    "shorts": self.HORARIOS_OTIMOS[Platform.SHORTS],
                },
            },
            "keywords_detectadas": self._extract_keywords(transcription)[:10],
        }

    def detect_archetype(self, text: str) -> Archetype:
        text_lower = (text or "").lower()
        patterns = {
            Archetype.DESPERTAR: ["descobri", "acordei", "abri os olhos"],
            Archetype.TENSAO: ["suspeito", "errado", "inquietante"],
            Archetype.CONFRONTO: ["discordo", "mentira", "farsa"],
            Archetype.VIRADA: ["virada", "reviravolta", "mudou tudo"],
            Archetype.REVELACAO: ["segredo", "revelar", "verdade"],
            Archetype.JUSTO_ENGOLIDO: ["enganado", "iludido", "manipulado"],
            Archetype.TRANSFORMACAO: ["transformei", "antes e depois", "mudei"],
            Archetype.RESOLUCAO: ["resolvi", "solução", "acabou"],
            Archetype.IMPACTO: ["chocante", "números", "dados"],
            Archetype.ENCERRAMENTO: ["conclusão", "lição", "final"],
        }
        scores = {a: 0 for a in Archetype}
        for a, words in patterns.items():
            scores[a] += sum(1 for w in words if w in text_lower)
        top = max(scores, key=scores.get)
        return top if scores[top] > 0 else Archetype.REVELACAO

    def _score_curiosity(self, text: str) -> float:
        text_lower = (text or "").lower()
        score = 45.0 + sum(8 for w in self.PALAVRAS_GANCHO if w in text_lower)
        score += text.count("?") * 4 + text.count("...") * 2
        return min(100.0, score)

    def _score_urgency(self, text: str) -> float:
        text_lower = (text or "").lower()
        urgency = ["agora", "urgente", "hoje", "antes que", "alerta"]
        score = 40.0 + sum(10 for w in urgency if w in text_lower) + text.count("!") * 3
        return min(100.0, score)

    def _score_emotion(self, text: str) -> float:
        text_lower = (text or "").lower()
        score = 45.0 + sum(10 for w in self.PALAVRAS_SHARE if w in text_lower)
        return min(100.0, score)

    def generate_hooks(self, cut: Cut, archetype: Optional[Archetype] = None) -> List[Dict[str, Any]]:
        arch = archetype or self.detect_archetype(cut.text)
        templates = self.HOOK_TEMPLATES.get(arch, self.HOOK_TEMPLATES[Archetype.REVELACAO])
        tema = (self._extract_keywords(cut.text) or ["conteúdo"])[0]
        selected = random.sample(templates, min(3, len(templates)))
        hooks = []
        for template in selected:
            hook = template.format(tema=tema)
            sc = (self._score_curiosity(hook) + self._score_urgency(hook) + self._score_emotion(hook)) / 3.0
            hooks.append(
                {
                    "hook": hook,
                    "archetype": arch.value,
                    "scoring": {
                        "curiosidade": round(self._score_curiosity(hook), 1),
                        "urgencia": round(self._score_urgency(hook), 1),
                        "emocao": round(self._score_emotion(hook), 1),
                        "total": round(sc, 1),
                    },
                }
            )
        hooks.sort(key=lambda x: x["scoring"]["total"], reverse=True)
        return hooks

    def _estimate_retention(self, text: str, duration: float) -> float:
        first_words = " ".join((text or "").lower().split()[:10])
        score = 55.0 + sum(12 for w in self.PALAVRAS_GANCHO if w in first_words)
        if 15 <= duration <= 45:
            score += 10
        if duration > 90:
            score -= 15
        return min(100.0, max(0.0, score))

    def _estimate_shareability(self, text: str) -> float:
        text_lower = (text or "").lower()
        score = 35.0 + sum(10 for w in self.PALAVRAS_SHARE if w in text_lower)
        if any(w in text_lower for w in ["todo mundo", "ninguém", "milhares"]):
            score += 8
        return min(100.0, score)

    def _estimate_commentability(self, text: str) -> float:
        text_lower = (text or "").lower()
        score = 30.0 + sum(10 for w in self.PALAVRAS_COMENTARIO if w in text_lower)
        if any(w in text_lower for w in ["discordo", "verdade", "mentira"]):
            score += 12
        return min(100.0, score)

    def _estimate_watch_time(self, text: str, duration: float) -> float:
        words = len((text or "").split())
        density = words / max(duration, 1.0)
        score = 45.0
        if 2 <= density <= 4:
            score += 20
        elif density > 5:
            score -= 10
        return min(100.0, max(0.0, score))

    def _suggest_platform(self, text: str, duration: float, viral_score: float) -> Platform:
        text_lower = (text or "").lower()
        tiktok = (2 if duration <= 30 else 0) + (1 if viral_score > 75 else 0)
        reels = (2 if 30 <= duration <= 60 else 0) + (1 if viral_score > 60 else 0)
        shorts = (2 if duration <= 45 else 0) + (3 if "como" in text_lower or "tutorial" in text_lower else 0)
        scores = {Platform.TIKTOK: tiktok, Platform.REELS: reels, Platform.SHORTS: shorts}
        return max(scores, key=scores.get)

    def _classify_score(self, score: float) -> str:
        if score >= 80:
            return "EXCELENTE"
        if score >= 60:
            return "BOM"
        if score >= 40:
            return "REGULAR"
        return "BAIXO"

    def _suggest_duration(self, platform: Platform, score: float) -> str:
        if platform == Platform.TIKTOK:
            return "15-30s" if score > 70 else "30-45s"
        if platform == Platform.REELS:
            return "30-60s" if score > 65 else "15-30s"
        return "30-45s"

    def _suggest_improvements(self, viral_score: float, ret: float, share: float) -> List[str]:
        out = []
        if viral_score < 60:
            out.append("Refaça o gancho inicial com frase mais forte.")
        if ret < 50:
            out.append("Aumente impacto nos primeiros 3 segundos.")
        if share < 50:
            out.append("Adicione elemento emocional ou contraste forte.")
        return out or ["Corte pronto para produção."]

    def score_cut(self, cut_text: str, duration: float) -> Dict[str, Any]:
        ret = self._estimate_retention(cut_text, duration)
        share = self._estimate_shareability(cut_text)
        com = self._estimate_commentability(cut_text)
        wt = self._estimate_watch_time(cut_text, duration)
        score = ret * 0.35 + share * 0.30 + com * 0.20 + wt * 0.15
        arch = self.detect_archetype(cut_text)
        hooks = self.generate_hooks(Cut(id="tmp", text=cut_text, duration=duration), arch)
        platform = self._suggest_platform(cut_text, duration, score)
        return {
            "viral_score": round(score, 1),
            "classificacao": self._classify_score(score),
            "metricas": {
                "retencao_estimada": round(ret, 1),
                "shareability": round(share, 1),
                "comentabilidade": round(com, 1),
                "watch_time_potencial": round(wt, 1),
            },
            "analise_conteudo": {
                "archetype_detectado": arch.value,
            },
            "recomendacoes": {
                "melhor_plataforma": platform.value,
                "hooks_sugeridos": hooks,
                "duracao_otima": self._suggest_duration(platform, score),
                "pontos_melhoria": self._suggest_improvements(score, ret, share),
            },
        }

    def rank_cuts(self, cuts_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        scored = []
        for item in cuts_list:
            cut = Cut(
                id=item.get("id", str(random.randint(1000, 9999))),
                text=item.get("text", ""),
                duration=float(item.get("duration", 30.0)),
            )
            analysis = self.score_cut(cut.text, cut.duration)
            cut.viral_score = analysis["viral_score"]
            cut.platform = Platform(analysis["recomendacoes"]["melhor_plataforma"])
            cut.hooks = [x["hook"] for x in analysis["recomendacoes"]["hooks_sugeridos"]]
            scored.append({"cut": cut, "full_analysis": analysis})

        scored.sort(key=lambda x: x["cut"].viral_score, reverse=True)
        excelentes = [x for x in scored if x["cut"].viral_score >= 80]
        bons = [x for x in scored if 60 <= x["cut"].viral_score < 80]
        regulares = [x for x in scored if 40 <= x["cut"].viral_score < 60]
        ruins = [x for x in scored if x["cut"].viral_score < 40]
        matar = [x["cut"].id for x in scored if x["cut"].viral_score < 60]
        total = len(cuts_list) or 1

        return {
            "ranking_geral": [
                {
                    "rank": i + 1,
                    "cut_id": row["cut"].id,
                    "viral_score": row["cut"].viral_score,
                    "classificacao": row["full_analysis"]["classificacao"],
                    "melhor_plataforma": row["cut"].platform.value,
                    "top_hook": row["cut"].hooks[0] if row["cut"].hooks else None,
                }
                for i, row in enumerate(scored)
            ],
            "categorias": {
                "excelentes_80plus": len(excelentes),
                "bons_60_79": len(bons),
                "regulares_40_59": len(regulares),
                "ruins_menos40": len(ruins),
            },
            "recomendacoes_producao": {
                "prioridade_maxima": [x["cut"].id for x in excelentes],
                "produzir_se_houver_tempo": [x["cut"].id for x in bons],
                "descartar_ou_reformular": matar,
            },
            "estimativa_performance": {
                "potencial_viral": len(excelentes) > 0,
                "volume_total_analisado": len(cuts_list),
                "taxa_aprovacao": f"{((len(excelentes) + len(bons)) / total * 100):.1f}%",
            },
        }

    def optimize_for_platform(self, cut: Cut, platform: Platform) -> Dict[str, Any]:
        specs = {
            Platform.TIKTOK: {"aspect_ratio": "9:16", "resolucao_recomendada": "1080x1920", "duracao_max": 60},
            Platform.REELS: {"aspect_ratio": "9:16", "resolucao_recomendada": "1080x1920", "duracao_max": 90},
            Platform.SHORTS: {"aspect_ratio": "9:16", "resolucao_recomendada": "1080x1920", "duracao_max": 60},
        }
        keywords = self._extract_keywords(cut.text)[:3]
        title = " ".join(keywords).title() if keywords else "Conteúdo Viral"
        hashtags_base = [f"#{k}" for k in keywords[:3]] or ["#viral", "#conteudo"]
        if platform == Platform.TIKTOK:
            hashtags = hashtags_base + ["#fyp", "#fy"]
        elif platform == Platform.REELS:
            hashtags = hashtags_base + ["#reels", "#instagram"]
        else:
            hashtags = hashtags_base + ["#shorts", "#youtube"]
        hook = cut.hooks[0] if cut.hooks else self.generate_hooks(cut)[0]["hook"]
        return {
            "plataforma": platform.value,
            "especificacoes_tecnicas": specs[platform],
            "textos_sugeridos": {
                "titulo_otimizado": title,
                "hashtags": hashtags,
                "legenda_hook": hook,
            },
        }
