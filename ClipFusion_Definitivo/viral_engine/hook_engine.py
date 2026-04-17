import random

class ViralHookEngine:
    def generate(self, tema="conteúdo", nicho="geral", platform="tiktok", archetype_id="revelacao"):
        hooks = {
            "despertar": f"Você não vai acreditar no que descobri sobre {tema}...",
            "tensao": f"O que vou te contar sobre {tema} pode te deixar irritado...",
            "confronto": f"Discordo 100% de quem fala assim sobre {tema}.",
            "virada": f"Pensei que entendia {tema} até descobrir isso...",
            "revelacao": f"O segredo que os experts em {tema} escondem de você.",
            "justo_engolido": f"Fui enganado sobre {tema} por anos... até hoje.",
            "transformacao": f"Como {tema} transformou minha vida completamente.",
            "resolucao": f"Resolvi meu maior problema com {tema} assim...",
            "impacto": f"Isso sobre {tema} vai chocar você.",
            "encerramento": f"E foi assim que {tema} mudou minha vida para sempre."
        }
        gancho = hooks.get(archetype_id, hooks["revelacao"])
        return {
            "gancho_final": gancho,
            "archetype": archetype_id,
            "score": round(random.uniform(70, 95), 1)
        }
