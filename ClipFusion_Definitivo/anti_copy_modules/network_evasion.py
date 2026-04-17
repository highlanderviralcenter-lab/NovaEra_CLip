class NetworkEvasion:
    def __init__(self, seed=42): pass
    def generate_schedule(self, count, platform): return [f"{h:02d}:00" for h in range(8,8+count)]
    def format_schedule(self, sched): return "\n".join(sched)
