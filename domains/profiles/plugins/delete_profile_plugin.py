from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class DeleteProfileResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class DeleteProfilePlugin(BasePlugin):
    def __init__(self, http, db, event_bus, auth, logger):
        self.http = http
        self.db = db
        self.bus = event_bus
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/{id}", "DELETE", self.execute,
            tags=["Profiles"],
            response_model=DeleteProfileResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            profile_id = int(data.get("id"))

            # Verify ownership
            existing = await self.db.query_one(
                "SELECT id, user_id FROM profiles WHERE id = $1", [profile_id]
            )
            if not existing:
                return {"success": False, "error": "Profile not found"}
            if existing["user_id"] != user_id:
                return {"success": False, "error": "Forbidden: not your profile"}

            # Cascade delete handles photos
            await self.db.execute("DELETE FROM profiles WHERE id = $1", [profile_id])

            self.logger.info(f"Profile {profile_id} deleted for user {user_id}")
            await self.bus.publish("profile.deleted", {"id": profile_id, "user_id": user_id})

            return {"success": True, "data": {"deleted": profile_id}}

        except Exception as e:
            self.logger.error(f"Failed to delete profile: {e}")
            return {"success": False, "error": str(e)}
