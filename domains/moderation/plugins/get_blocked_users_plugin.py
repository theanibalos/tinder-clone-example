from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class BlockedUserData(BaseModel):
    id: int
    blocked_id: int
    blocked_name: str | None = None
    created_at: str | None = None


class GetBlockedUsersResponse(BaseModel):
    success: bool
    data: Optional[list[BlockedUserData]] = None
    error: Optional[str] = None


class GetBlockedUsersPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/blocks", "GET", self.execute,
            tags=["Moderation"],
            response_model=GetBlockedUsersResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))

            rows = await self.db.query(
                """SELECT b.id, b.blocked_id, p.name as blocked_name, b.created_at
                   FROM blocks b
                   LEFT JOIN profiles p ON p.user_id = b.blocked_id
                   WHERE b.blocker_id = $1
                   ORDER BY b.created_at DESC""",
                [user_id]
            )

            return {"success": True, "data": [dict(r) for r in rows]}

        except Exception as e:
            self.logger.error(f"Error fetching blocked users: {e}")
            return {"success": False, "error": str(e)}
