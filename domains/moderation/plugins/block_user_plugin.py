from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class BlockUserRequest(BaseModel):
    blocked_id: int


# ── Response schema ──────────────────────────────────────────────────────────
class BlockUserResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class BlockUserPlugin(BasePlugin):
    def __init__(self, http, db, event_bus, auth, logger):
        self.http = http
        self.db = db
        self.bus = event_bus
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/blocks", "POST", self.execute,
            tags=["Moderation"],
            request_model=BlockUserRequest,
            response_model=BlockUserResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            blocker_id = int(auth_payload.get("sub"))
            req = BlockUserRequest(**data)

            if blocker_id == req.blocked_id:
                return {"success": False, "error": "Cannot block yourself"}

            existing = await self.db.query_one(
                "SELECT id FROM blocks WHERE blocker_id = $1 AND blocked_id = $2",
                [blocker_id, req.blocked_id]
            )
            if existing:
                return {"success": False, "error": "User already blocked"}

            async with self.db.transaction() as tx:
                block_id = await tx.execute(
                    "INSERT INTO blocks (blocker_id, blocked_id) VALUES ($1, $2) RETURNING id",
                    [blocker_id, req.blocked_id]
                )
                await tx.execute(
                    """UPDATE matches SET is_active = 0
                       WHERE (user_a_id = $1 AND user_b_id = $2)
                          OR (user_a_id = $3 AND user_b_id = $4)""",
                    [blocker_id, req.blocked_id, req.blocked_id, blocker_id]
                )

            self.logger.info(f"User {blocker_id} blocked user {req.blocked_id}")
            await self.bus.publish("user.blocked", {
                "blocker_id": blocker_id,
                "blocked_id": req.blocked_id,
            })

            return {"success": True, "data": {"id": block_id, "blocked_id": req.blocked_id}}

        except Exception as e:
            self.logger.error(f"Failed to block user: {e}")
            return {"success": False, "error": str(e)}
