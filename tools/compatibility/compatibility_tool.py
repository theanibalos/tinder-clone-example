"""
Compatibility Tool — Extensible Scoring Engine for MicroCoreOS
===============================================================

Strategy pattern: swap algorithms at runtime or via config.
New strategies are auto-discoverable — just add a file in strategies/.

PUBLIC CONTRACT:
────────────────
    score = await compatibility.score(viewer_profile, candidate_profile)
    ranked = await compatibility.rank(viewer_profile, candidates)
    compatibility.set_strategy("weighted")
    name = compatibility.get_strategy_name()
    names = compatibility.list_strategies()
"""

import os
from core.base_tool import BaseTool
from tools.compatibility.strategies.base_strategy import BaseCompatibilityStrategy
from tools.compatibility.strategies.simple_strategy import SimpleStrategy
from tools.compatibility.strategies.weighted_strategy import WeightedStrategy
from tools.compatibility.strategies.elo_strategy import EloStrategy
from tools.compatibility.strategies.ml_strategy import MlStrategy


class CompatibilityTool(BaseTool):
    """Pluggable compatibility scoring engine.

    Selects a scoring strategy based on COMPATIBILITY_STRATEGY env var.
    Default: 'simple'. Available: 'simple', 'weighted', 'elo', 'ml'.

    Extensible: add a new strategy class in tools/compatibility/strategies/
    and register it in _STRATEGIES.
    """

    # ── Registry of available strategies ──────────────────────
    _STRATEGIES: dict[str, type[BaseCompatibilityStrategy]] = {
        "simple": SimpleStrategy,
        "weighted": WeightedStrategy,
        "elo": EloStrategy,
        "ml": MlStrategy,
    }

    # ── IDENTITY ─────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "compatibility"

    # ── CONSTRUCTOR ──────────────────────────────────────────

    def __init__(self) -> None:
        self._strategy_name: str = os.getenv("COMPATIBILITY_STRATEGY", "simple")
        self._strategy: BaseCompatibilityStrategy | None = None

    # ── LIFECYCLE ────────────────────────────────────────────

    def setup(self) -> None:
        self._strategy = self._load_strategy(self._strategy_name)
        print(f"[Compatibility] Strategy: {self._strategy_name}")

    def on_boot_complete(self, container) -> None:
        pass

    def shutdown(self) -> None:
        pass

    # ── PRIVATE ──────────────────────────────────────────────

    def _load_strategy(self, name: str) -> BaseCompatibilityStrategy:
        cls = self._STRATEGIES.get(name)
        if cls is None:
            available = ", ".join(self._STRATEGIES.keys())
            raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
        return cls()

    # ── PUBLIC API ───────────────────────────────────────────

    async def score(self, viewer_profile: dict, candidate_profile: dict, context: dict | None = None) -> float:
        """Score compatibility between two profiles (0.0–1.0)."""
        return await self._strategy.score(viewer_profile, candidate_profile, context)

    async def rank(self, viewer_profile: dict, candidates: list[dict], context: dict | None = None) -> list[dict]:
        """Rank candidates by compatibility score descending. Adds _score to each."""
        return await self._strategy.rank(viewer_profile, candidates, context)

    def set_strategy(self, name: str) -> None:
        """Switch to a different strategy at runtime."""
        self._strategy = self._load_strategy(name)
        self._strategy_name = name
        print(f"[Compatibility] Strategy switched to: {name}")

    def get_strategy_name(self) -> str:
        """Return the name of the currently active strategy."""
        return self._strategy_name

    def list_strategies(self) -> list[str]:
        """Return all available strategy names."""
        return list(self._STRATEGIES.keys())

    @classmethod
    def register_strategy(cls, strategy_class: type[BaseCompatibilityStrategy]) -> None:
        """Register a new strategy at runtime (e.g., from a plugin)."""
        instance = strategy_class()
        cls._STRATEGIES[instance.strategy_name] = strategy_class
        print(f"[Compatibility] New strategy registered: {instance.strategy_name}")

    # ── INTERFACE DESCRIPTION ────────────────────────────────

    def get_interface_description(self) -> str:
        return """
        Compatibility Scoring Tool (compatibility):
        - PURPOSE: Extensible algorithm engine for ranking discovery candidates.
          Uses the Strategy pattern — swap algorithms via config or at runtime.
        - CONFIGURATION: Set COMPATIBILITY_STRATEGY env var ('simple', 'weighted', 'elo', 'ml').
        - CAPABILITIES:
            - await score(viewer_profile, candidate_profile, context?) → float: 0.0–1.0 score.
            - await rank(viewer_profile, candidates, context?) → list[dict]: Sorted by _score desc.
            - set_strategy(name): Switch algorithm at runtime.
            - get_strategy_name() → str: Current strategy name.
            - list_strategies() → list[str]: All available strategy names.
            - register_strategy(cls): Register a new strategy class at runtime.
        """
