"""
PreferenceEntity — Mirror of the `preferences` table in the database.

RULE: This file contains ONE thing: the DB entity.
      HTTP request/response schemas belong inside each plugin.
      Do NOT add request models here.
"""

from pydantic import BaseModel


class PreferenceEntity(BaseModel):
    id: int | None = None
    user_id: int
    interested_in_gender: str  # 'male', 'female', 'everyone'
    min_age: int = 18
    max_age: int = 99
    max_distance_km: int = 100
