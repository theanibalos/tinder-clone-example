"""
SwipeEntity — Mirror of the `swipes` table in the database.

RULE: This file contains ONE thing: the DB entity.
      HTTP request/response schemas belong inside each plugin.
      Do NOT add request models here.
"""

from pydantic import BaseModel


class SwipeEntity(BaseModel):
    id: int | None = None
    swiper_id: int
    swiped_id: int
    action: str  # 'like', 'pass', 'superlike'
    created_at: str | None = None
