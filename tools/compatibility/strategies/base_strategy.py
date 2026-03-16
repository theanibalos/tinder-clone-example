from abc import ABC, abstractmethod


class BaseCompatibilityStrategy(ABC):
    """Abstract interface for compatibility scoring algorithms.

    To create a new strategy:
    1. Subclass this in tools/compatibility/strategies/
    2. Implement score() and rank()
    3. The strategy is auto-discoverable by name via the compatibility tool
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Unique identifier for this strategy (e.g., 'simple', 'weighted', 'elo')."""
        ...

    @abstractmethod
    async def score(self, viewer_profile: dict, candidate_profile: dict, context: dict | None = None) -> float:
        """Return a 0.0–1.0 compatibility score between two profiles.

        Args:
            viewer_profile: The user viewing the discovery feed.
            candidate_profile: A potential match candidate.
            context: Optional data (e.g., swipe history, shared interests).

        Returns:
            Float between 0.0 (no compatibility) and 1.0 (perfect match).
        """
        ...

    @abstractmethod
    async def rank(self, viewer_profile: dict, candidates: list[dict], context: dict | None = None) -> list[dict]:
        """Return candidates sorted by compatibility score descending.

        Each candidate dict gets a `_score` field added.

        Args:
            viewer_profile: The user viewing the discovery feed.
            candidates: List of candidate profile dicts.
            context: Optional data for scoring.

        Returns:
            Sorted list with `_score` added to each candidate.
        """
        ...
