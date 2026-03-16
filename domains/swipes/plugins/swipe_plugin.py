from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class SwipeRequest(BaseModel):
    swiped_id: int
    action: str  # 'like', 'pass', 'superlike'


# ── Response schema ──────────────────────────────────────────────────────────
class SwipeData(BaseModel):
    id: int
    swiper_id: int
    swiped_id: int
    action: str


class SwipeResponse(BaseModel):
    success: bool
    data: Optional[SwipeData] = None
    error: Optional[str] = None


class SwipePlugin(BasePlugin):
    def __init__(self, http, db, event_bus, auth, logger):
        self.http = http
        self.db = db
        self.bus = event_bus
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/swipes", "POST", self.execute,
            tags=["Swipes"],
            request_model=SwipeRequest,
            response_model=SwipeResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            swiper_id = int(auth_payload.get("sub"))
            req = SwipeRequest(**data)

            if req.action not in ("like", "pass", "superlike"):
                return {"success": False, "error": "Invalid action. Must be: like, pass, superlike"}

            if swiper_id == req.swiped_id:
                return {"success": False, "error": "Cannot swipe yourself"}

            # Check if already swiped
            existing = await self.db.query_one(
                "SELECT id FROM swipes WHERE swiper_id = $1 AND swiped_id = $2",
                [swiper_id, req.swiped_id]
            )
            if existing:
                return {"success": False, "error": "Already swiped on this user"}

            # Verify target profile exists
            target = await self.db.query_one(
                "SELECT id FROM profiles WHERE user_id = $1", [req.swiped_id]
            )
            if not target:
                return {"success": False, "error": "Target profile not found"}

            swipe_id = await self.db.execute(
                """INSERT INTO swipes (swiper_id, swiped_id, action)
                   VALUES ($1, $2, $3) RETURNING id""",
                [swiper_id, req.swiped_id, req.action]
            )

            self.logger.info(f"Swipe {req.action} from {swiper_id} to {req.swiped_id}")
            await self.bus.publish("swipe.created", {
                "id": swipe_id,
                "swiper_id": swiper_id,
                "swiped_id": req.swiped_id,
                "action": req.action,
            })

            return {
                "success": True,
                "data": {
                    "id": swipe_id,
                    "swiper_id": swiper_id,
                    "swiped_id": req.swiped_id,
                    "action": req.action,
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to swipe: {e}")
            return {"success": False, "error": str(e)}
