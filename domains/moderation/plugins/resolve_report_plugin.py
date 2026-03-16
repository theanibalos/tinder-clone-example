from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Request schema ───────────────────────────────────────────────────────────
class ResolveReportRequest(BaseModel):
    status: str  # 'reviewed', 'resolved', 'dismissed'


# ── Response schema ──────────────────────────────────────────────────────────
class ResolveReportResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class ResolveReportPlugin(BasePlugin):
    """Admin endpoint: update report status. In production, add admin role check."""

    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/admin/reports/{id}", "PUT", self.execute,
            tags=["Admin"],
            request_model=ResolveReportRequest,
            response_model=ResolveReportResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            # TODO: Add admin role check
            report_id = int(data.get("id"))
            req = ResolveReportRequest(**data)

            if req.status not in ("reviewed", "resolved", "dismissed"):
                return {"success": False, "error": "Invalid status"}

            report = await self.db.query_one(
                "SELECT id FROM reports WHERE id = $1", [report_id]
            )
            if not report:
                return {"success": False, "error": "Report not found"}

            await self.db.execute(
                "UPDATE reports SET status = $1 WHERE id = $2",
                [req.status, report_id]
            )

            self.logger.info(f"Report {report_id} → {req.status}")
            return {"success": True, "data": {"id": report_id, "status": req.status}}

        except Exception as e:
            self.logger.error(f"Failed to resolve report: {e}")
            return {"success": False, "error": str(e)}
