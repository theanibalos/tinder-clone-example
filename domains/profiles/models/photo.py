"""
PhotoEntity — Mirror of the `photos` table in the database.

RULE: This file contains ONE thing: the DB entity.
      HTTP request/response schemas belong inside each plugin.
      Do NOT add request models here.
"""

from pydantic import BaseModel


class PhotoEntity(BaseModel):
    id: int | None = None
    profile_id: int
    file_path: str
    position: int = 0  # ordering within the profile (0-5)
    created_at: str | None = None
