import random
class AIEvasion:
    def __init__(self, seed: int): self.rng = random.Random(seed)
    def ffmpeg_filters(self) -> list:
        filters = ["vignette=angle=PI/5:mode=backward", f"setpts=PTS+{self.rng.uniform(0.0001,0.0003):.5f}*random(0)", f"gblur=sigma={self.rng.uniform(0.2,0.4):.2f}"]
        return filters
