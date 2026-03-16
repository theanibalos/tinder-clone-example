from core.base_plugin import BasePlugin


class CheckMatchPlugin(BasePlugin):
    """Event-driven plugin: subscribes to swipe.created and creates a match when mutual like is detected."""

    def __init__(self, db, event_bus, logger):
        self.db = db
        self.bus = event_bus
        self.logger = logger

    async def on_boot(self):
        await self.bus.subscribe("swipe.created", self._on_swipe)

    async def _on_swipe(self, data: dict):
        try:
            swiper_id = data.get("swiper_id")
            swiped_id = data.get("swiped_id")
            action = data.get("action")

            # Only check for matches on likes and superlikes
            if action not in ("like", "superlike"):
                return

            # Check if the other person also liked us
            reverse_swipe = await self.db.query_one(
                """SELECT id, action FROM swipes
                   WHERE swiper_id = $1 AND swiped_id = $2 AND action IN ('like', 'superlike')""",
                [swiped_id, swiper_id]
            )

            if not reverse_swipe:
                return  # No mutual like yet

            # Check if match already exists
            # NOTE: SQLite positional params — each $N needs its own param
            existing_match = await self.db.query_one(
                """SELECT id FROM matches
                   WHERE (user_a_id = $1 AND user_b_id = $2)
                      OR (user_a_id = $3 AND user_b_id = $4)""",
                [swiper_id, swiped_id, swiped_id, swiper_id]
            )

            if existing_match:
                return  # Already matched

            # Create the match (order by smaller ID first for consistency)
            user_a = min(swiper_id, swiped_id)
            user_b = max(swiper_id, swiped_id)

            match_id = await self.db.execute(
                "INSERT INTO matches (user_a_id, user_b_id) VALUES ($1, $2) RETURNING id",
                [user_a, user_b]
            )

            self.logger.info(f"🔥 Match created! ID={match_id} between users {user_a} and {user_b}")

            await self.bus.publish("match.created", {
                "id": match_id,
                "user_a_id": user_a,
                "user_b_id": user_b,
            })

        except Exception as e:
            self.logger.error(f"Error checking match: {e}")
