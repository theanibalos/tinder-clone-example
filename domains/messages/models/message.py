"""
MessageEntity — Mirror of the `messages` table in the database.

RULE: This file contains ONE thing: the DB entity.
      HTTP request/response schemas belong inside each plugin.
      Do NOT add request models here.
"""

from pydantic import BaseModel


class MessageEntity(BaseModel):
    id: int | None = None
    match_id: int
    sender_id: int
    content: str
    content_type: str = "text"  # 'text', 'image', 'gif'
    is_read: bool = False
    created_at: str | None = None
