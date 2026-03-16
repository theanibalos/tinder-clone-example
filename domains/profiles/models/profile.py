"""
ProfileEntity — Mirror of the `profiles` table in the database.

RULE: This file contains ONE thing: the DB entity.
      HTTP request/response schemas belong inside each plugin.
      Do NOT add request models here.
"""

from pydantic import BaseModel


class ProfileEntity(BaseModel):
    id: int | None = None
    user_id: int
    name: str
    bio: str | None = None
    age: int
    gender: str  # 'male', 'female', 'non_binary', 'other'
    latitude: float | None = None
    longitude: float | None = None
    is_verified: bool = False
    created_at: str | None = None
    updated_at: str | None = None
