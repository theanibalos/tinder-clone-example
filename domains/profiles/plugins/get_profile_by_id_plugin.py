from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class PhotoData(BaseModel):
    id: int
    file_path: str
    position: int


class ProfileData(BaseModel):
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


class GetProfileByIdResponse(BaseModel):
    success: bool
    data: Optional[ProfileData] = None
    error: Optional[str] = None


class GetProfileByIdPlugin(BasePlugin):
    def __init__(self, http, db, logger):
        self.http = http
        self.db = db
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/{id}", "GET", self.execute,
            tags=["Profiles"],
            response_model=GetProfileByIdResponse,
        )

    async def execute(self, data: dict, context=None):
        try:
            profile_id = int(data.get("id"))

            row = await self.db.query_one(
                """SELECT id, user_id, name, bio, age, gender, latitude, longitude,
                          is_verified, created_at, updated_at
                   FROM profiles WHERE id = $1""",
                [profile_id]
            )

            if not row:
                return {"success": False, "error": "Profile not found"}

            photos = await self.db.query(
                "SELECT id, file_path, position FROM photos WHERE profile_id = $1 ORDER BY position",
                [profile_id]
            )

            profile_data = dict(row)
            profile_data["is_verified"] = bool(profile_data.get("is_verified", 0))
            profile_data["photos"] = [dict(p) for p in photos]

            return {"success": True, "data": profile_data}

        except Exception as e:
            self.logger.error(f"Error fetching profile {data.get('id')}: {e}")
            return {"success": False, "error": str(e)}
