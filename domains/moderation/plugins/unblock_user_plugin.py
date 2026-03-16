from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class UnblockUserResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class UnblockUserPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/blocks/{id}", "DELETE", self.execute,
            tags=["Moderation"],
            response_model=UnblockUserResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            block_id = int(data.get("id"))

            block = await self.db.query_one(
                "SELECT id, blocker_id FROM blocks WHERE id = $1", [block_id]
            )
            if not block:
                return {"success": False, "error": "Block not found"}
            if block["blocker_id"] != user_id:
                return {"success": False, "error": "Forbidden"}

            await self.db.execute("DELETE FROM blocks WHERE id = $1", [block_id])

            self.logger.info(f"Block {block_id} removed by user {user_id}")
            return {"success": True, "data": {"unblocked": block_id}}

        except Exception as e:
            self.logger.error(f"Failed to unblock: {e}")
            return {"success": False, "error": str(e)}
