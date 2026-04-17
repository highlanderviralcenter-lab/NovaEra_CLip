PLATFORM_SPECS = {
    "tiktok": {"max_hook_chars": 100, "max_duration": 180, "ideal": (30, 60), "label": "TikTok"},
    "instagram": {"max_hook_chars": 125, "max_duration": 90, "ideal": (15, 60), "label": "Instagram Reels"},
    "youtube": {"max_hook_chars": 70, "max_duration": 60, "ideal": (15, 60), "label": "YouTube Shorts"},
    "kwai": {"max_hook_chars": 100, "max_duration": 60, "ideal": (15, 60), "label": "Kwai"},
}


class PlatformOptimizer:
    @staticmethod
    def optimize(hook: str, platform: str) -> str:
        limit = PLATFORM_SPECS.get(platform, {}).get("max_hook_chars", 100)
        return hook[:limit - 3] + "..." if len(hook) > limit else hook

    @staticmethod
    def specs(platform: str) -> dict:
        return PLATFORM_SPECS.get(platform, PLATFORM_SPECS["tiktok"])
