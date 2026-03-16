import math
from tools.compatibility.strategies.base_strategy import BaseCompatibilityStrategy


class WeightedStrategy(BaseCompatibilityStrategy):
    """Multi-factor weighted scoring:
    - 0.3 × distance_score (closer = higher)
    - 0.3 × age_compatibility (smaller gap = higher)
    - 0.2 × shared_interests (keyword overlap in bios)
    - 0.2 × bio_similarity (both have bios = bonus)
    """

    WEIGHTS = {
        "distance": 0.3,
        "age": 0.3,
        "interests": 0.2,
        "bio": 0.2,
    }

    @property
    def strategy_name(self) -> str:
        return "weighted"

    async def score(self, viewer_profile: dict, candidate_profile: dict, context: dict | None = None) -> float:
        scores = {
            "distance": self._distance_score(viewer_profile, candidate_profile),
            "age": self._age_score(viewer_profile, candidate_profile),
            "interests": self._interest_score(viewer_profile, candidate_profile),
            "bio": self._bio_score(viewer_profile, candidate_profile),
        }

        total = sum(self.WEIGHTS[k] * scores[k] for k in self.WEIGHTS)
        return round(min(max(total, 0.0), 1.0), 4)

    async def rank(self, viewer_profile: dict, candidates: list[dict], context: dict | None = None) -> list[dict]:
        for candidate in candidates:
            candidate["_score"] = await self.score(viewer_profile, candidate, context)
        return sorted(candidates, key=lambda c: c["_score"], reverse=True)

    def _distance_score(self, viewer: dict, candidate: dict) -> float:
        """Closer profiles score higher. Max distance considered: 200km."""
        v_lat, v_lon = viewer.get("latitude"), viewer.get("longitude")
        c_lat, c_lon = candidate.get("latitude"), candidate.get("longitude")

        if not all([v_lat, v_lon, c_lat, c_lon]):
            return 0.5  # Neutral if no location

        # Haversine
        lat1, lon1 = math.radians(v_lat), math.radians(v_lon)
        lat2, lon2 = math.radians(c_lat), math.radians(c_lon)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        distance_km = 6371 * 2 * math.asin(math.sqrt(a))

        max_distance = 200
        return max(0.0, 1.0 - (distance_km / max_distance))

    def _age_score(self, viewer: dict, candidate: dict) -> float:
        """Smaller age gap = higher score."""
        v_age = viewer.get("age", 25)
        c_age = candidate.get("age", 25)
        gap = abs(v_age - c_age)

        # 0 gap = 1.0, 20+ gap = 0.0
        return max(0.0, 1.0 - (gap / 20))

    def _interest_score(self, viewer: dict, candidate: dict) -> float:
        """Simple keyword overlap between bios."""
        v_bio = (viewer.get("bio") or "").lower()
        c_bio = (candidate.get("bio") or "").lower()

        if not v_bio or not c_bio:
            return 0.3  # Low neutral

        # Extract words (simple tokenization)
        stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
                      "i", "me", "my", "you", "your", "we", "our", "in", "on", "at",
                      "to", "for", "of", "with", "like", "love", "enjoy", "really"}

        v_words = set(w for w in v_bio.split() if len(w) > 2 and w not in stop_words)
        c_words = set(w for w in c_bio.split() if len(w) > 2 and w not in stop_words)

        if not v_words or not c_words:
            return 0.3

        overlap = len(v_words & c_words)
        union = len(v_words | c_words)
        jaccard = overlap / union if union > 0 else 0

        return min(1.0, jaccard * 3)  # Amplify small overlaps

    def _bio_score(self, viewer: dict, candidate: dict) -> float:
        """Bonus for having a bio (indicates effort/engagement)."""
        v_bio = viewer.get("bio") or ""
        c_bio = candidate.get("bio") or ""

        if len(c_bio) > 100:
            return 1.0
        elif len(c_bio) > 50:
            return 0.7
        elif len(c_bio) > 0:
            return 0.4
        return 0.0
