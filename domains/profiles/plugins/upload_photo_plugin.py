import os
from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class UploadedPhotoData(BaseModel):
    id: int
    profile_id: int
    file_path: str
    position: int


class UploadPhotoResponse(BaseModel):
    success: bool
    data: Optional[UploadedPhotoData] = None
    error: Optional[str] = None


MAX_PHOTOS = 6


class UploadPhotoPlugin(BasePlugin):
    def __init__(self, http, db, auth, config, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.config = config
        self.logger = logger
        self.upload_dir = None

    async def on_boot(self):
        self.upload_dir = self.config.get("UPLOAD_DIR", default="uploads/photos")
        os.makedirs(self.upload_dir, exist_ok=True)

        self.http.add_endpoint(
            "/profiles/{id}/photos", "POST", self.execute,
            tags=["Profiles"],
            response_model=UploadPhotoResponse,
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
            profile = await self.db.query_one(
                "SELECT id, user_id FROM profiles WHERE id = $1", [profile_id]
            )
            if not profile:
                return {"success": False, "error": "Profile not found"}
            if profile["user_id"] != user_id:
                return {"success": False, "error": "Forbidden: not your profile"}

            # Check photo limit
            photo_count = await self.db.query_one(
                "SELECT COUNT(*) as count FROM photos WHERE profile_id = $1", [profile_id]
            )
            if photo_count and photo_count["count"] >= MAX_PHOTOS:
                return {"success": False, "error": f"Maximum {MAX_PHOTOS} photos allowed"}

            # For MVP: store file_path reference (actual file upload handled by client)
            file_path = data.get("file_path")
            if not file_path:
                return {"success": False, "error": "file_path is required"}

            position = photo_count["count"] if photo_count else 0

            photo_id = await self.db.execute(
                """INSERT INTO photos (profile_id, file_path, position)
                   VALUES ($1, $2, $3) RETURNING id""",
                [profile_id, file_path, position]
            )

            self.logger.info(f"Photo {photo_id} uploaded for profile {profile_id}")

            return {
                "success": True,
                "data": {
                    "id": photo_id,
                    "profile_id": profile_id,
                    "file_path": file_path,
                    "position": position,
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to upload photo: {e}")
            return {"success": False, "error": str(e)}
