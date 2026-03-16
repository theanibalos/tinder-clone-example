from tools.compatibility.strategies.base_strategy import BaseCompatibilityStrategy


class MlStrategy(BaseCompatibilityStrategy):
    """Machine Learning-ready compatibility strategy.

    This is a stub that provides the interface for a trained ML model.
    To activate:
    1. Set COMPATIBILITY_MODEL_PATH env var to the model file
    2. Implement feature engineering in _extract_features()
    3. Load model in __init__ or lazy-load on first call

    The model should accept a feature vector and return a [0, 1] compatibility score.
    """

    @property
    def strategy_name(self) -> str:
        return "ml"

    def __init__(self):
        self._model = None

    def _load_model(self):
        """Lazy-load ML model. Override to implement actual model loading."""
        import os
        model_path = os.getenv("COMPATIBILITY_MODEL_PATH")
        if not model_path:
            return None

        # Example (uncomment when model is available):
        # import joblib
        # self._model = joblib.load(model_path)
        return None

    def _extract_features(self, viewer: dict, candidate: dict) -> list[float]:
        """Extract feature vector from two profiles.

        Override this to implement your feature engineering pipeline.
        Example features:
        - Age difference
        - Distance
        - Bio length ratio
        - Shared interest count
        - Swipe history patterns
        """
        import math

        v_age = viewer.get("age", 25)
        c_age = candidate.get("age", 25)
        age_diff = abs(v_age - c_age) / 50.0  # Normalized

        # Distance (normalized)
        v_lat, v_lon = viewer.get("latitude", 0), viewer.get("longitude", 0)
        c_lat, c_lon = candidate.get("latitude", 0), candidate.get("longitude", 0)
        if v_lat and v_lon and c_lat and c_lon:
            lat1, lon1 = math.radians(v_lat), math.radians(v_lon)
            lat2, lon2 = math.radians(c_lat), math.radians(c_lon)
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
            distance_km = 6371 * 2 * math.asin(math.sqrt(a))
            distance_norm = min(1.0, distance_km / 200)
        else:
            distance_norm = 0.5

        # Bio engagement
        v_bio_len = len(viewer.get("bio") or "") / 500
        c_bio_len = len(candidate.get("bio") or "") / 500

        return [age_diff, distance_norm, v_bio_len, c_bio_len]

    async def score(self, viewer_profile: dict, candidate_profile: dict, context: dict | None = None) -> float:
        if self._model is None:
            self._load_model()

        features = self._extract_features(viewer_profile, candidate_profile)

        if self._model is not None:
            # prediction = self._model.predict([features])[0]
            # return float(min(max(prediction, 0.0), 1.0))
            pass

        # Fallback: simple weighted average of features
        weights = [0.3, 0.3, 0.2, 0.2]
        # Invert age_diff and distance (lower = better)
        adjusted = [1 - features[0], 1 - features[1], features[2], features[3]]
        score = sum(w * f for w, f in zip(weights, adjusted))
        return round(min(max(score, 0.0), 1.0), 4)

    async def rank(self, viewer_profile: dict, candidates: list[dict], context: dict | None = None) -> list[dict]:
        for candidate in candidates:
            candidate["_score"] = await self.score(viewer_profile, candidate, context)
        return sorted(candidates, key=lambda c: c["_score"], reverse=True)
