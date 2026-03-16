"""
MatchEntity — Mirror of the `matches` table in the database.

RULE: This file contains ONE thing: the DB entity.
      HTTP request/response schemas belong inside each plugin.
      Do NOT add request models here.
"""

from pydantic import BaseModel


class MatchEntity(BaseModel):
    id: int | None = None
    user_a_id: int
    user_b_id: int
    matched_at: str | None = None
    is_active: bool = True
