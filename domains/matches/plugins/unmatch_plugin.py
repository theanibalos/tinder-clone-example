from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class UnmatchResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class UnmatchPlugin(BasePlugin):
    def __init__(self, http, db, event_bus, auth, logger):
        self.http = http
        self.db = db
        self.bus = event_bus
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/matches/{match_id}", "DELETE", self.execute,
            tags=["Matches"],
            response_model=UnmatchResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            match_id = int(data.get("match_id"))

            match = await self.db.query_one(
                """SELECT id, user_a_id, user_b_id FROM matches
                   WHERE id = $1 AND (user_a_id = $2 OR user_b_id = $3)""",
                [match_id, user_id, user_id]
            )

            if not match:
                return {"success": False, "error": "Match not found"}

            await self.db.execute(
                "UPDATE matches SET is_active = 0 WHERE id = $1", [match_id]
            )

            self.logger.info(f"Match {match_id} deactivated by user {user_id}")
            await self.bus.publish("match.unmatched", {
                "id": match_id,
                "user_a_id": match["user_a_id"],
                "user_b_id": match["user_b_id"],
                "unmatched_by": user_id,
            })

            return {"success": True, "data": {"unmatched": match_id}}

        except Exception as e:
            self.logger.error(f"Failed to unmatch: {e}")
            return {"success": False, "error": str(e)}
