from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class UpdatePreferencesRequest(BaseModel):
    interested_in_gender: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    max_distance_km: int | None = None


# ── Response schema ──────────────────────────────────────────────────────────
class PreferenceData(BaseModel):
    id: int
    user_id: int
    interested_in_gender: str
    min_age: int
    max_age: int
    max_distance_km: int


class UpdatePreferencesResponse(BaseModel):
    success: bool
    data: Optional[PreferenceData] = None
    error: Optional[str] = None


class UpdatePreferencesPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/profiles/me/preferences", "PUT", self.execute,
            tags=["Profiles"],
            request_model=UpdatePreferencesRequest,
            response_model=UpdatePreferencesResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))

            existing = await self.db.query_one(
                "SELECT id FROM preferences WHERE user_id = $1", [user_id]
            )
            if not existing:
                return {"success": False, "error": "Preferences not set yet. Use POST first."}

            req = UpdatePreferencesRequest(**data)
            updates = req.model_dump(exclude_none=True, exclude={"_auth"})

            if not updates:
                return {"success": False, "error": "No fields to update"}

            set_clauses = []
            values = []
            for i, (key, value) in enumerate(updates.items(), 1):
                set_clauses.append(f"{key} = ${i}")
                values.append(value)

            values.append(user_id)
            placeholder = len(values)

            await self.db.execute(
                f"UPDATE preferences SET {', '.join(set_clauses)} WHERE user_id = ${placeholder}",
                values
            )

            row = await self.db.query_one(
                """SELECT id, user_id, interested_in_gender, min_age, max_age, max_distance_km
                   FROM preferences WHERE user_id = $1""",
                [user_id]
            )

            self.logger.info(f"Preferences updated for user {user_id}")

            return {"success": True, "data": dict(row)}

        except Exception as e:
            self.logger.error(f"Failed to update preferences: {e}")
            return {"success": False, "error": str(e)}
