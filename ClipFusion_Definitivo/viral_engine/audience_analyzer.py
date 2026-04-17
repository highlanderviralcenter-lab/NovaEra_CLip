from viral_engine.analysis_engine import ViralEngine


class AudienceAnalyzer:
    def __init__(self):
        self.engine = ViralEngine()

    def analyze(self, nicho, platform):
        # Mantém compatibilidade com assinatura antiga e retorna timings.
        fake_text = f"{nicho} {platform}"
        audience = self.engine.analyze_audience(fake_text)
        timing = audience.get("comportamento", {}).get("horarios_otimos_postagem", {}).get(platform, [])
        return {"timing_otimo": timing or ["09:00", "13:00", "18:00"], "audience": audience}
