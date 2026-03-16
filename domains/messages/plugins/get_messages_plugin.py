from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class MessageData(BaseModel):
    id: int
    sender_id: int
    content: str
    content_type: str
    is_read: bool
    created_at: str | None = None


class GetMessagesResponse(BaseModel):
    success: bool
    data: Optional[list[MessageData]] = None
    error: Optional[str] = None


class GetMessagesPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/matches/{match_id}/messages", "GET", self.execute,
            tags=["Messages"],
            response_model=GetMessagesResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            match_id = int(data.get("match_id"))
            limit = int(data.get("limit", 50))
            offset = int(data.get("offset", 0))

            # Verify user is part of this match
            match = await self.db.query_one(
                """SELECT id FROM matches
                   WHERE id = $1 AND (user_a_id = $2 OR user_b_id = $3)""",
                [match_id, user_id, user_id]
            )
            if not match:
                return {"success": False, "error": "Match not found"}

            rows = await self.db.query(
                """SELECT id, sender_id, content, content_type, is_read, created_at
                   FROM messages
                   WHERE match_id = $1
                   ORDER BY created_at ASC
                   LIMIT $2 OFFSET $3""",
                [match_id, limit, offset]
            )

            results = []
            for row in rows:
                item = dict(row)
                item["is_read"] = bool(item.get("is_read", 0))
                results.append(item)

            return {"success": True, "data": results}

        except Exception as e:
            self.logger.error(f"Error fetching messages: {e}")
            return {"success": False, "error": str(e)}
