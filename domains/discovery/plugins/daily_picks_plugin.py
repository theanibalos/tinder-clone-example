from datetime import date
from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class PhotoData(BaseModel):
    id: int
    file_path: str
    position: int


class DailyPickProfile(BaseModel):
    profile_id: int
    user_id: int
    name: str
    bio: str | None = None
    age: int
    gender: str
    photos: list[PhotoData] = []


class DailyPicksResponse(BaseModel):
    success: bool
    data: Optional[list[DailyPickProfile]] = None
    error: Optional[str] = None


class DailyPicksPlugin(BasePlugin):
    def __init__(self, http, db, auth, state, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.state = state
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/discovery/daily-picks", "GET", self.execute,
            tags=["Discovery"],
            response_model=DailyPicksResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))

            cache_key = f"daily_picks_{user_id}_{date.today().isoformat()}"
            cached = self.state.get(cache_key, namespace="discovery")
            if cached:
                return {"success": True, "data": cached}

            prefs = await self.db.query_one(
                """SELECT interested_in_gender, min_age, max_age
                   FROM preferences WHERE user_id = $1""",
                [user_id]
            )
            if not prefs:
                return {"success": False, "error": "Set your preferences first"}

            gender_filter = ""
            params = [user_id, user_id, prefs["min_age"], prefs["max_age"], user_id]
            if prefs["interested_in_gender"] != "everyone":
                gender_filter = "AND p.gender = $6"
                params.append(prefs["interested_in_gender"])

            rows = await self.db.query(
                f"""SELECT p.id as profile_id, p.user_id, p.name, p.bio, p.age, p.gender,
                           CASE WHEN s.action = 'superlike' THEN 2
                                WHEN s.action = 'like' THEN 1
                                ELSE 0 END as priority
                    FROM profiles p
                    LEFT JOIN swipes s ON s.swiper_id = p.user_id AND s.swiped_id = $1
                    WHERE p.user_id != $2
                      AND p.age BETWEEN $3 AND $4
                      AND p.user_id NOT IN (
                          SELECT swiped_id FROM swipes WHERE swiper_id = $5
                      )
                      {gender_filter}
                    ORDER BY priority DESC, RANDOM()
                    LIMIT 10""",
                params
            )

            if not rows:
                return {"success": True, "data": []}

            # Batch load all photos in a single query
            profile_ids = [row["profile_id"] for row in rows]
            placeholders = ", ".join(f"${i + 1}" for i in range(len(profile_ids)))
            all_photos = await self.db.query(
                f"SELECT id, profile_id, file_path, position FROM photos "
                f"WHERE profile_id IN ({placeholders}) ORDER BY profile_id, position",
                profile_ids
            )

            photos_by_profile: dict[int, list] = {}
            for photo in all_photos:
                pid = photo["profile_id"]
                photos_by_profile.setdefault(pid, []).append({
                    "id": photo["id"],
                    "file_path": photo["file_path"],
                    "position": photo["position"],
                })

            results = [
                {
                    "profile_id": row["profile_id"],
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "bio": row["bio"],
                    "age": row["age"],
                    "gender": row["gender"],
                    "photos": photos_by_profile.get(row["profile_id"], []),
                }
                for row in rows
            ]

            self.state.set(cache_key, results, namespace="discovery")
            return {"success": True, "data": results}

        except Exception as e:
            self.logger.error(f"Error generating daily picks: {e}")
            return {"success": False, "error": str(e)}
