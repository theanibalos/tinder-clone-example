from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class MarkReadResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class MarkReadPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/notifications/{id}/read", "PUT", self.execute,
            tags=["Notifications"],
            response_model=MarkReadResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            notif_id = int(data.get("id"))

            notif = await self.db.query_one(
                "SELECT id, user_id FROM notifications WHERE id = $1",
                [notif_id]
            )

            if not notif:
                return {"success": False, "error": "Notification not found"}
            if notif["user_id"] != user_id:
                return {"success": False, "error": "Forbidden"}

            await self.db.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = $1", [notif_id]
            )

            return {"success": True, "data": {"marked_read": notif_id}}

        except Exception as e:
            self.logger.error(f"Error marking notification as read: {e}")
            return {"success": False, "error": str(e)}
