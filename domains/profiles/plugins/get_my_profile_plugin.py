from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class PhotoData(BaseModel):
    id: int
    file_path: str
    position: int


class MyProfileData(BaseModel):
    id: int
    user_id: int
    name: str
    bio: str | None = None
    age: int
    gender: str
    latitude: float | None = None
    longitude: float | None = None
    is_verified: bool
    photos: list[PhotoData] = []
    created_at: str | None = None
    updated_at: str | None = None


class GetMyProfileResponse(BaseModel):
    success: bool
    data: Optional[MyProfileData] = None
    error: Optional[str] = None


class GetMyProfilePlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/me", "GET", self.execute,
            tags=["Profiles"],
            response_model=GetMyProfileResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))

            row = await self.db.query_one(
                """SELECT id, user_id, name, bio, age, gender, latitude, longitude,
                          is_verified, created_at, updated_at
                   FROM profiles WHERE user_id = $1""",
                [user_id]
            )

            if not row:
                return {"success": False, "error": "Profile not found"}

            profile_data = dict(row)
            profile_data["is_verified"] = bool(profile_data.get("is_verified", 0))

            photos = await self.db.query(
                "SELECT id, file_path, position FROM photos WHERE profile_id = $1 ORDER BY position",
                [profile_data["id"]]
            )
            profile_data["photos"] = [dict(p) for p in photos]

            return {"success": True, "data": profile_data}

        except Exception as e:
            self.logger.error(f"Error in /profiles/me: {e}")
            return {"success": False, "error": str(e)}
