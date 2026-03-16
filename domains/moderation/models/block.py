"""
BlockEntity — Mirror of the `blocks` table in the database.

RULE: This file contains ONE thing: the DB entity.
"""

from pydantic import BaseModel


class BlockEntity(BaseModel):
    id: int | None = None
    blocker_id: int
    blocked_id: int
    created_at: str | None = None
