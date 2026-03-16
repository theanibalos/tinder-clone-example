from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class DeletePhotoResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class DeletePhotoPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/{id}/photos/{photo_id}", "DELETE", self.execute,
            tags=["Profiles"],
            response_model=DeletePhotoResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            profile_id = int(data.get("id"))
            photo_id = int(data.get("photo_id"))

            # Verify profile ownership
            profile = await self.db.query_one(
                "SELECT id, user_id FROM profiles WHERE id = $1", [profile_id]
            )
            if not profile:
                return {"success": False, "error": "Profile not found"}
            if profile["user_id"] != user_id:
                return {"success": False, "error": "Forbidden: not your profile"}

            # Verify photo belongs to profile
            photo = await self.db.query_one(
                "SELECT id FROM photos WHERE id = $1 AND profile_id = $2",
                [photo_id, profile_id]
            )
            if not photo:
                return {"success": False, "error": "Photo not found"}

            await self.db.execute("DELETE FROM photos WHERE id = $1", [photo_id])

            # Reorder remaining photos
            remaining = await self.db.query(
                "SELECT id FROM photos WHERE profile_id = $1 ORDER BY position", [profile_id]
            )
            for i, row in enumerate(remaining):
                await self.db.execute(
                    "UPDATE photos SET position = $1 WHERE id = $2", [i, row["id"]]
                )

            self.logger.info(f"Photo {photo_id} deleted from profile {profile_id}")

            return {"success": True, "data": {"deleted": photo_id}}

        except Exception as e:
            self.logger.error(f"Failed to delete photo: {e}")
            return {"success": False, "error": str(e)}
