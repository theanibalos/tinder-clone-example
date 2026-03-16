from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class MatchProfile(BaseModel):
    user_id: int
    name: str
    age: int
    gender: str
    photo: str | None = None


class MatchData(BaseModel):
    id: int
    matched_user: MatchProfile
    matched_at: str | None = None


class GetMatchesResponse(BaseModel):
    success: bool
    data: Optional[list[MatchData]] = None
    error: Optional[str] = None


class GetMatchesPlugin(BasePlugin):
    def __init__(self, http, db, auth, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/matches", "GET", self.execute,
            tags=["Matches"],
            response_model=GetMatchesResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))

            rows = await self.db.query(
                """SELECT m.id, m.matched_at,
                          p.user_id, p.name, p.age, p.gender,
                          (SELECT ph.file_path FROM photos ph
                           WHERE ph.profile_id = p.id
                           ORDER BY ph.position LIMIT 1) as photo
                   FROM matches m
                   JOIN profiles p ON p.user_id = CASE
                       WHEN m.user_a_id = $1 THEN m.user_b_id
                       ELSE m.user_a_id
                   END
                   WHERE (m.user_a_id = $2 OR m.user_b_id = $3)
                     AND m.is_active = 1
                   ORDER BY m.matched_at DESC""",
                [user_id, user_id, user_id]
            )

            results = [
                {
                    "id": row["id"],
                    "matched_user": {
                        "user_id": row["user_id"],
                        "name": row["name"],
                        "age": row["age"],
                        "gender": row["gender"],
                        "photo": row["photo"],
                    },
                    "matched_at": row["matched_at"],
                }
                for row in rows
            ]

            return {"success": True, "data": results}

        except Exception as e:
            self.logger.error(f"Error fetching matches: {e}")
            return {"success": False, "error": str(e)}
