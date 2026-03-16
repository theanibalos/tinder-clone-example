from core.base_plugin import BasePlugin


class MatchNotificationPlugin(BasePlugin):
    """Event-driven: listens for match.created and swipe.created (superlikes) to create notifications."""

    def __init__(self, db, event_bus, logger):
        self.db = db
        self.bus = event_bus
        self.logger = logger

    async def on_boot(self):
        await self.bus.subscribe("match.created", self._on_match)
        await self.bus.subscribe("swipe.created", self._on_swipe)

    async def _on_match(self, data: dict):
        try:
            user_a_id = data.get("user_a_id")
            user_b_id = data.get("user_b_id")
            match_id = data.get("id")

            # Get names for notification text
            profile_a = await self.db.query_one(
                "SELECT name FROM profiles WHERE user_id = $1", [user_a_id]
            )
            profile_b = await self.db.query_one(
                "SELECT name FROM profiles WHERE user_id = $1", [user_b_id]
            )

            name_a = profile_a["name"] if profile_a else "Someone"
            name_b = profile_b["name"] if profile_b else "Someone"

            # Notify both users
            await self.db.execute(
                """INSERT INTO notifications (user_id, type, title, body, reference_id)
                   VALUES ($1, 'match', $2, $3, $4)""",
                [user_a_id, "It's a Match! 🔥", f"You and {name_b} liked each other!", match_id]
            )
            await self.db.execute(
                """INSERT INTO notifications (user_id, type, title, body, reference_id)
                   VALUES ($1, 'match', $2, $3, $4)""",
                [user_b_id, "It's a Match! 🔥", f"You and {name_a} liked each other!", match_id]
            )

            self.logger.info(f"Match notifications sent for match {match_id}")

        except Exception as e:
            self.logger.error(f"Error creating match notification: {e}")

    async def _on_swipe(self, data: dict):
        try:
            if data.get("action") != "superlike":
                return

            swiper_id = data.get("swiper_id")
            swiped_id = data.get("swiped_id")

            swiper_profile = await self.db.query_one(
                "SELECT name FROM profiles WHERE user_id = $1", [swiper_id]
            )
            swiper_name = swiper_profile["name"] if swiper_profile else "Someone"

            await self.db.execute(
                """INSERT INTO notifications (user_id, type, title, body, reference_id)
                   VALUES ($1, 'superlike', $2, $3, $4)""",
                [swiped_id, "Super Like! ⭐", f"{swiper_name} super liked you!", swiper_id]
            )

            self.logger.info(f"Superlike notification sent to user {swiped_id}")

        except Exception as e:
            self.logger.error(f"Error creating superlike notification: {e}")
