from core.base_plugin import BasePlugin


class CreateProfileOnUserCreatedPlugin(BasePlugin):
    """
    Plugin that listens for 'user.created' and automatically creates 
    a default profile for the new user.
    """
    def __init__(self, db, event_bus, logger):
        self.db = db
        self.bus = event_bus
        self.logger = logger

    async def on_boot(self):
        # Subscribe to user creation event
        await self.bus.subscribe("user.created", self.handle_user_created)

    async def handle_user_created(self, event_data: dict):
        try:
            user_id = event_data.get("id")
            name = event_data.get("name", "New User")
            
            # Use provided data or defaults
            age = event_data.get("age") or 18
            gender = event_data.get("gender") or "other"
            latitude = event_data.get("latitude")
            longitude = event_data.get("longitude")
            
            self.logger.info(f"Auto-creating profile for user {user_id}...")

            # Check if profile already exists (safety check)
            existing = await self.db.query_one(
                "SELECT id FROM profiles WHERE user_id = $1", [user_id]
            )
            if existing:
                self.logger.warning(f"Profile already exists for user {user_id}, skipping auto-creation.")
                return

            profile_id = await self.db.execute(
                """INSERT INTO profiles (user_id, name, age, gender, latitude, longitude)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                [user_id, name, age, gender, latitude, longitude]
            )

            self.logger.info(f"Auto-profile created with ID {profile_id} for user {user_id}")
            await self.bus.publish("profile.created", {"id": profile_id, "user_id": user_id, "auto_created": True})

        except Exception as e:
            self.logger.error(f"Failed to auto-create profile for user {event_data.get('id')}: {e}")
