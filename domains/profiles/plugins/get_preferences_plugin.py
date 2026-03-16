from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class PreferenceData(BaseModel):
    id: int
    user_id: int
    interested_in_gender: str
    min_age: int
    max_age: int
    max_distance_km: int


class GetPreferencesResponse(BaseModel):
    success: bool
    data: Optional[PreferenceData] = None
    error: Optional[str] = None


class GetPreferencesPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/me/preferences", "GET", self.execute,
            tags=["Profiles"],
            response_model=GetPreferencesResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))

            row = await self.db.query_one(
                """SELECT id, user_id, interested_in_gender, min_age, max_age, max_distance_km
                   FROM preferences WHERE user_id = $1""",
                [user_id]
            )

            if not row:
                return {"success": False, "error": "Preferences not set yet"}

            return {"success": True, "data": dict(row)}

        except Exception as e:
            self.logger.error(f"Error fetching preferences: {e}")
            return {"success": False, "error": str(e)}
