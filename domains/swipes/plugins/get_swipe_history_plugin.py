from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class SwipeHistoryItem(BaseModel):
    id: int
    swiped_id: int
    swiped_name: str
    action: str
    created_at: str | None = None


class GetSwipeHistoryResponse(BaseModel):
    success: bool
    data: Optional[list[SwipeHistoryItem]] = None
    error: Optional[str] = None


class GetSwipeHistoryPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/swipes/history", "GET", self.execute,
            tags=["Swipes"],
            response_model=GetSwipeHistoryResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            limit = int(data.get("limit", 50))
            offset = int(data.get("offset", 0))

            rows = await self.db.query(
                """SELECT s.id, s.swiped_id, p.name as swiped_name, s.action, s.created_at
                   FROM swipes s
                   JOIN profiles p ON p.user_id = s.swiped_id
                   WHERE s.swiper_id = $1
                   ORDER BY s.created_at DESC
                   LIMIT $2 OFFSET $3""",
                [user_id, limit, offset]
            )

            return {"success": True, "data": [dict(r) for r in rows]}

        except Exception as e:
            self.logger.error(f"Error fetching swipe history: {e}")
            return {"success": False, "error": str(e)}
