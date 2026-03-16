from tools.compatibility.strategies.base_strategy import BaseCompatibilityStrategy


class SimpleStrategy(BaseCompatibilityStrategy):
    """Binary compatibility: 1.0 if not already swiped, 0.0 otherwise.

    This is the baseline strategy — discovery feed order is essentially random
    among profiles that haven't been swiped yet.
    """

    @property
    def strategy_name(self) -> str:
        return "simple"

    async def score(self, viewer_profile: dict, candidate_profile: dict, context: dict | None = None) -> float:
        # In simple mode, all unswiped candidates get equal score
        return 1.0

    async def rank(self, viewer_profile: dict, candidates: list[dict], context: dict | None = None) -> list[dict]:
        for candidate in candidates:
            candidate["_score"] = await self.score(viewer_profile, candidate, context)
        return candidates  # No reordering in simple mode
