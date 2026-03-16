from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class ReportUserRequest(BaseModel):
    reported_id: int
    reason: str


# ── Response schema ──────────────────────────────────────────────────────────
class ReportData(BaseModel):
    id: int
    reporter_id: int
    reported_id: int
    reason: str
    status: str


class ReportUserResponse(BaseModel):
    success: bool
    data: Optional[ReportData] = None
    error: Optional[str] = None


class ReportUserPlugin(BasePlugin):
    def __init__(self, http, db, event_bus, auth, logger):
        self.http = http
        self.db = db
        self.bus = event_bus
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/reports", "POST", self.execute,
            tags=["Moderation"],
            request_model=ReportUserRequest,
            response_model=ReportUserResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            reporter_id = int(auth_payload.get("sub"))
            req = ReportUserRequest(**data)

            if reporter_id == req.reported_id:
                return {"success": False, "error": "Cannot report yourself"}

            report_id = await self.db.execute(
                """INSERT INTO reports (reporter_id, reported_id, reason)
                   VALUES ($1, $2, $3) RETURNING id""",
                [reporter_id, req.reported_id, req.reason]
            )

            self.logger.info(f"Report {report_id}: user {reporter_id} reported user {req.reported_id}")
            await self.bus.publish("user.reported", {
                "id": report_id,
                "reporter_id": reporter_id,
                "reported_id": req.reported_id,
                "reason": req.reason,
            })

            return {
                "success": True,
                "data": {
                    "id": report_id,
                    "reporter_id": reporter_id,
                    "reported_id": req.reported_id,
                    "reason": req.reason,
                    "status": "pending",
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to report user: {e}")
            return {"success": False, "error": str(e)}
