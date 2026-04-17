class SecondaryGroupStrategy:
    def dual_hook(self, hook: str, primary: str, secondary: dict) -> str: angle = secondary.get("angulo_gancho", ""); return f"{hook} ({angle})" if angle else hook
    def expansion_report(self, primary: str, secondary: dict) -> str: return f"Público primário: {primary}\nExpansão: {secondary.get('nome','')} (+{secondary.get('expansao_potencial','?')} alcance estimado)"
