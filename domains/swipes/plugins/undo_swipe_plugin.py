from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class UndoSwipeResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class UndoSwipePlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/swipes/undo", "POST", self.execute,
            tags=["Swipes"],
            response_model=UndoSwipeResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))

            # Find last swipe by this user
            last_swipe = await self.db.query_one(
                """SELECT id, swiped_id, action FROM swipes
                   WHERE swiper_id = $1
                   ORDER BY created_at DESC LIMIT 1""",
                [user_id]
            )

            if not last_swipe:
                return {"success": False, "error": "No swipes to undo"}

            await self.db.execute("DELETE FROM swipes WHERE id = $1", [last_swipe["id"]])

            self.logger.info(f"User {user_id} undid swipe {last_swipe['id']}")

            return {
                "success": True,
                "data": {
                    "undone_swipe_id": last_swipe["id"],
                    "swiped_id": last_swipe["swiped_id"],
                    "action": last_swipe["action"],
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to undo swipe: {e}")
            return {"success": False, "error": str(e)}
