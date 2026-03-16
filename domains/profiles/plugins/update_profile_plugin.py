from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class UpdateProfileRequest(BaseModel):
    name: str | None = None
    bio: str | None = None
    age: int | None = None
    gender: str | None = None
    latitude: float | None = None
    longitude: float | None = None


# ── Response schema ──────────────────────────────────────────────────────────
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


class UpdateProfileResponse(BaseModel):
    success: bool
    data: Optional[ProfileData] = None
    error: Optional[str] = None


class UpdateProfilePlugin(BasePlugin):
    def __init__(self, http, db, event_bus, auth, logger):
        self.http = http
        self.db = db
        self.bus = event_bus
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/{id}", "PUT", self.execute,
            tags=["Profiles"],
            request_model=UpdateProfileRequest,
            response_model=UpdateProfileResponse,
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

            req = UpdateProfileRequest(**data)
            updates = req.model_dump(exclude_none=True, exclude={"id", "_auth"})

            if not updates:
                return {"success": False, "error": "No fields to update"}

            set_clauses = []
            values = []
            for i, (key, value) in enumerate(updates.items(), 1):
                set_clauses.append(f"{key} = ${i}")
                values.append(value)

            values.append(profile_id)
            placeholder = len(values)

            await self.db.execute(
                f"UPDATE profiles SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ${placeholder}",
                values
            )

            row = await self.db.query_one(
                """SELECT id, user_id, name, bio, age, gender, latitude, longitude, is_verified
                   FROM profiles WHERE id = $1""",
                [profile_id]
            )

            profile_data = dict(row)
            profile_data["is_verified"] = bool(profile_data.get("is_verified", 0))

            self.logger.info(f"Profile {profile_id} updated")
            await self.bus.publish("profile.updated", {"id": profile_id, "user_id": user_id})

            return {"success": True, "data": profile_data}

        except Exception as e:
            self.logger.error(f"Failed to update profile: {e}")
            return {"success": False, "error": str(e)}
