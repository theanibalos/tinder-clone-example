"""
ReportEntity — Mirror of the `reports` table in the database.

RULE: This file contains ONE thing: the DB entity.
"""

from pydantic import BaseModel


class ReportEntity(BaseModel):
    id: int | None = None
    reporter_id: int
    reported_id: int
    reason: str
    status: str = "pending"  # 'pending', 'reviewed', 'resolved', 'dismissed'
    created_at: str | None = None
