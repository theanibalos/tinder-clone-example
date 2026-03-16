from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class ReportData(BaseModel):
    id: int
    reporter_id: int
    reported_id: int
    reason: str
    status: str
    created_at: str | None = None


class GetReportsResponse(BaseModel):
    success: bool
    data: Optional[list[ReportData]] = None
    error: Optional[str] = None


class GetReportsPlugin(BasePlugin):
    """Admin endpoint: lists all reports. In production, add admin role check."""

    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/admin/reports", "GET", self.execute,
            tags=["Admin"],
            response_model=GetReportsResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            # TODO: Add admin role check
            status_filter = data.get("status")
            limit = int(data.get("limit", 50))

            if status_filter:
                rows = await self.db.query(
                    """SELECT id, reporter_id, reported_id, reason, status, created_at
                       FROM reports WHERE status = $1
                       ORDER BY created_at DESC LIMIT $2""",
                    [status_filter, limit]
                )
            else:
                rows = await self.db.query(
                    """SELECT id, reporter_id, reported_id, reason, status, created_at
                       FROM reports
                       ORDER BY created_at DESC LIMIT $1""",
                    [limit]
                )

            return {"success": True, "data": [dict(r) for r in rows]}

        except Exception as e:
            self.logger.error(f"Error fetching reports: {e}")
            return {"success": False, "error": str(e)}
