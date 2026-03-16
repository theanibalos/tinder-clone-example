from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class MarkMessageReadResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class MarkMessageReadPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/messages/{id}/read", "PUT", self.execute,
            tags=["Messages"],
            response_model=MarkMessageReadResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            message_id = int(data.get("id"))

            # Verify the message exists and user is part of the match
            msg = await self.db.query_one(
                """SELECT m.id, m.match_id, m.sender_id
                   FROM messages m
                   JOIN matches mt ON mt.id = m.match_id
                   WHERE m.id = $1 AND (mt.user_a_id = $2 OR mt.user_b_id = $3)""",
                [message_id, user_id, user_id]
            )

            if not msg:
                return {"success": False, "error": "Message not found"}

            # Only mark as read if the user is NOT the sender
            if msg["sender_id"] == user_id:
                return {"success": False, "error": "Cannot mark own message as read"}

            await self.db.execute(
                "UPDATE messages SET is_read = 1 WHERE id = $1", [message_id]
            )

            return {"success": True, "data": {"marked_read": message_id}}

        except Exception as e:
            self.logger.error(f"Error marking message as read: {e}")
            return {"success": False, "error": str(e)}
