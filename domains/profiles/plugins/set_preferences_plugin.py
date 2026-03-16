from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class SetPreferencesRequest(BaseModel):
    interested_in_gender: str = "everyone"  # 'male', 'female', 'everyone'
    min_age: int = 18
    max_age: int = 99
    max_distance_km: int = 100


# ── Response schema ──────────────────────────────────────────────────────────
class PreferenceData(BaseModel):
    id: int
    user_id: int
    interested_in_gender: str
    min_age: int
    max_age: int
    max_distance_km: int


class SetPreferencesResponse(BaseModel):
    success: bool
    data: Optional[PreferenceData] = None
    error: Optional[str] = None


class SetPreferencesPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/me/preferences", "POST", self.execute,
            tags=["Profiles"],
            request_model=SetPreferencesRequest,
            response_model=SetPreferencesResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            req = SetPreferencesRequest(**data)

            # Check if preferences already exist
            existing = await self.db.query_one(
                "SELECT id FROM preferences WHERE user_id = $1", [user_id]
            )
            if existing:
                return {"success": False, "error": "Preferences already set. Use PUT to update."}

            pref_id = await self.db.execute(
                """INSERT INTO preferences (user_id, interested_in_gender, min_age, max_age, max_distance_km)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                [user_id, req.interested_in_gender, req.min_age, req.max_age, req.max_distance_km]
            )

            self.logger.info(f"Preferences set for user {user_id}")

            return {
                "success": True,
                "data": {
                    "id": pref_id,
                    "user_id": user_id,
                    "interested_in_gender": req.interested_in_gender,
                    "min_age": req.min_age,
                    "max_age": req.max_age,
                    "max_distance_km": req.max_distance_km,
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to set preferences: {e}")
            return {"success": False, "error": str(e)}
