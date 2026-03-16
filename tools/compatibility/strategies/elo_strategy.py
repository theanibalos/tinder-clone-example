from tools.compatibility.strategies.base_strategy import BaseCompatibilityStrategy


class EloStrategy(BaseCompatibilityStrategy):
    """ELO-based desirability ranking.

    Each user maintains an ELO rating that adjusts based on swipe patterns:
    - Getting liked increases your ELO
    - Getting passed decreases your ELO
    - High-ELO users see high-ELO candidates

    The scoring prioritizes candidates whose ELO is close to the viewer's ELO.
    """

    DEFAULT_ELO = 1000
    K_FACTOR = 32  # How much a single swipe adjusts ELO

    @property
    def strategy_name(self) -> str:
        return "elo"

    async def score(self, viewer_profile: dict, candidate_profile: dict, context: dict | None = None) -> float:
        viewer_elo = viewer_profile.get("_elo", self.DEFAULT_ELO)
        candidate_elo = candidate_profile.get("_elo", self.DEFAULT_ELO)

        # Score based on ELO proximity — closer ratings = higher score
        elo_diff = abs(viewer_elo - candidate_elo)
        max_diff = 500  # Beyond this difference, score approaches 0

        proximity_score = max(0.0, 1.0 - (elo_diff / max_diff))

        # Slight bonus for candidates with higher ELO (aspirational matching)
        if candidate_elo > viewer_elo:
            aspiration_bonus = min(0.15, (candidate_elo - viewer_elo) / 2000)
        else:
            aspiration_bonus = 0.0

        return round(min(1.0, proximity_score + aspiration_bonus), 4)

    async def rank(self, viewer_profile: dict, candidates: list[dict], context: dict | None = None) -> list[dict]:
        for candidate in candidates:
            candidate["_score"] = await self.score(viewer_profile, candidate, context)
        return sorted(candidates, key=lambda c: c["_score"], reverse=True)

    @staticmethod
    def calculate_new_elo(current_elo: int, was_liked: bool, other_elo: int, k_factor: int = 32) -> int:
        """Calculate ELO adjustment after a swipe.

        Args:
            current_elo: The profile's current ELO.
            was_liked: True if this profile was liked, False if passed.
            other_elo: The swiper's ELO.
            k_factor: Sensitivity (default 32).

        Returns:
            New ELO rating.
        """
        expected = 1 / (1 + 10 ** ((other_elo - current_elo) / 400))
        actual = 1.0 if was_liked else 0.0
        new_elo = current_elo + int(k_factor * (actual - expected))
        return max(100, new_elo)  # Floor at 100
