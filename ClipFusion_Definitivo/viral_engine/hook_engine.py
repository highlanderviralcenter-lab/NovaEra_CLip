from viral_engine.analysis_engine import Archetype, Cut, ViralEngine

class ViralHookEngine:
    def __init__(self):
        self.engine = ViralEngine()

    def generate(self, tema="conteúdo", nicho="geral", platform="tiktok", archetype_id="revelacao"):
        cut = Cut(id="hook", text=tema, duration=20.0)
        try:
            arch = Archetype(archetype_id)
        except Exception:
            arch = Archetype.REVELACAO
        hooks = self.engine.generate_hooks(cut, arch)
        best = hooks[0] if hooks else {"hook": f"O segredo sobre {tema}.", "scoring": {"total": 70.0}}
        return {
            "gancho_final": best["hook"],
            "archetype": arch.value,
            "score": best.get("scoring", {}).get("total", 70.0),
        }
