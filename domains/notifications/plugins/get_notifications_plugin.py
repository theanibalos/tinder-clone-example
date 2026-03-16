from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class NotificationData(BaseModel):
    id: int
    type: str
    title: str
    body: str
    is_read: bool
    reference_id: int | None = None
    created_at: str | None = None


class GetNotificationsResponse(BaseModel):
    success: bool
    data: Optional[list[NotificationData]] = None
    error: Optional[str] = None


class GetNotificationsPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/notifications", "GET", self.execute,
            tags=["Notifications"],
            response_model=GetNotificationsResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            limit = int(data.get("limit", 50))
            unread_only = data.get("unread_only", "false").lower() == "true"

            read_filter = "AND is_read = 0" if unread_only else ""

            rows = await self.db.query(
                f"""SELECT id, type, title, body, is_read, reference_id, created_at
                    FROM notifications
                    WHERE user_id = $1 {read_filter}
                    ORDER BY created_at DESC
                    LIMIT $2""",
                [user_id, limit]
            )

            results = []
            for row in rows:
                item = dict(row)
                item["is_read"] = bool(item.get("is_read", 0))
                results.append(item)

            return {"success": True, "data": results}

        except Exception as e:
            self.logger.error(f"Error fetching notifications: {e}")
            return {"success": False, "error": str(e)}
