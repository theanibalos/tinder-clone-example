from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class SendMessageRequest(BaseModel):
    content: str
    content_type: str = "text"  # 'text', 'image', 'gif'


# ── Response schema ──────────────────────────────────────────────────────────
class MessageData(BaseModel):
    id: int
    match_id: int
    sender_id: int
    content: str
    content_type: str
    created_at: str | None = None


class SendMessageResponse(BaseModel):
    success: bool
    data: Optional[MessageData] = None
    error: Optional[str] = None


class SendMessagePlugin(BasePlugin):
    def __init__(self, http, db, event_bus, auth, logger):
        self.http = http
        self.db = db
        self.bus = event_bus
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/matches/{match_id}/messages", "POST", self.execute,
            tags=["Messages"],
            request_model=SendMessageRequest,
            response_model=SendMessageResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            match_id = int(data.get("match_id"))
            req = SendMessageRequest(**data)

            # Verify user is part of this match and it's active
            match = await self.db.query_one(
                """SELECT id, user_a_id, user_b_id FROM matches
                   WHERE id = $1 AND (user_a_id = $2 OR user_b_id = $3) AND is_active = 1""",
                [match_id, user_id, user_id]
            )
            if not match:
                return {"success": False, "error": "Match not found or inactive"}

            msg_id = await self.db.execute(
                """INSERT INTO messages (match_id, sender_id, content, content_type)
                   VALUES ($1, $2, $3, $4) RETURNING id""",
                [match_id, user_id, req.content, req.content_type]
            )

            # Determine recipient
            recipient_id = match["user_b_id"] if match["user_a_id"] == user_id else match["user_a_id"]

            await self.bus.publish("message.sent", {
                "id": msg_id,
                "match_id": match_id,
                "sender_id": user_id,
                "recipient_id": recipient_id,
                "content": req.content,
                "content_type": req.content_type,
            })

            self.logger.info(f"Message {msg_id} sent in match {match_id}")

            return {
                "success": True,
                "data": {
                    "id": msg_id,
                    "match_id": match_id,
                    "sender_id": user_id,
                    "content": req.content,
                    "content_type": req.content_type,
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return {"success": False, "error": str(e)}
