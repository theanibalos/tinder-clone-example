"""
NotificationEntity — Mirror of the `notifications` table in the database.

RULE: This file contains ONE thing: the DB entity.
      HTTP request/response schemas belong inside each plugin.
      Do NOT add request models here.
"""

from pydantic import BaseModel


class NotificationEntity(BaseModel):
    id: int | None = None
    user_id: int
    type: str  # 'match', 'superlike', 'message'
    title: str
    body: str
    is_read: bool = False
    reference_id: int | None = None  # match_id, message_id, etc.
    created_at: str | None = None
