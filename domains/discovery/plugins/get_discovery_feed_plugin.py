import math
from typing import Optional
from pydantic import BaseModel
from core.base_plugin import BasePlugin


# ── Response schema ──────────────────────────────────────────────────────────
class PhotoData(BaseModel):
    id: int
    file_path: str
    position: int


class DiscoveryProfile(BaseModel):
    profile_id: int
    user_id: int
    name: str
    bio: str | None = None
    age: int
    gender: str
    distance_km: float | None = None
    photos: list[PhotoData] = []


class GetDiscoveryFeedResponse(BaseModel):
    success: bool
    data: Optional[list[DiscoveryProfile]] = None
    error: Optional[str] = None


class GetDiscoveryFeedPlugin(BasePlugin):
    def __init__(self, http, db, auth, compatibility, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.compatibility = compatibility
        self.logger = logger

    async def on_boot(self):
        self.http.add_endpoint(
            "/discovery", "GET", self.execute,
            tags=["Discovery"],
            response_model=GetDiscoveryFeedResponse,
            auth_validator=self.auth.validate_token,
        )

    async def execute(self, data: dict, context=None):
        try:
            auth_payload = data.get("_auth")
            if not auth_payload:
                return {"success": False, "error": "Unauthorized"}

            user_id = int(auth_payload.get("sub"))
            limit = int(data.get("limit", 20))

            # age included so we don't need a second query for compatibility ranking
            viewer = await self.db.query_one(
                "SELECT id, age, gender, latitude, longitude FROM profiles WHERE user_id = $1",
                [user_id]
            )
            if not viewer:
                return {"success": False, "error": "Create a profile first"}

            prefs = await self.db.query_one(
                """SELECT interested_in_gender, min_age, max_age, max_distance_km
                   FROM preferences WHERE user_id = $1""",
                [user_id]
            )
            if not prefs:
                return {"success": False, "error": "Set your preferences first"}

            # Fetch more than limit to account for distance filtering in Python
            fetch_limit = limit * 5
            gender_filter = ""
            params = [user_id, prefs["min_age"], prefs["max_age"], user_id, user_id, user_id, fetch_limit]
            if prefs["interested_in_gender"] != "everyone":
                gender_filter = "AND p.gender = $8"
                params.append(prefs["interested_in_gender"])

            rows = await self.db.query(
                f"""SELECT p.id as profile_id, p.user_id, p.name, p.bio, p.age, p.gender,
                           p.latitude, p.longitude
                    FROM profiles p
                    WHERE p.user_id != $1
                      AND p.age BETWEEN $2 AND $3
                      AND p.user_id NOT IN (
                          SELECT swiped_id FROM swipes WHERE swiper_id = $4
                      )
                      AND p.user_id NOT IN (
                          SELECT blocked_id FROM blocks WHERE blocker_id = $5
                      )
                      AND p.user_id NOT IN (
                          SELECT blocker_id FROM blocks WHERE blocked_id = $6
                      )
                      {gender_filter}
                    LIMIT $7""",
                params
            )

            v_lat = viewer.get("latitude")
            v_lon = viewer.get("longitude")

            def haversine(lat2, lon2):
                if not (v_lat and v_lon and lat2 and lon2):
                    return None
                r_lat1 = math.radians(v_lat)
                r_lon1 = math.radians(v_lon)
                r_lat2 = math.radians(lat2)
                r_lon2 = math.radians(lon2)
                dlat = r_lat2 - r_lat1
                dlon = r_lon2 - r_lon1
                a = math.sin(dlat / 2) ** 2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(dlon / 2) ** 2
                return round(6371 * 2 * math.asin(math.sqrt(a)), 1)

            # Apply distance filter and collect up to `limit` valid candidates
            filtered = []
            for row in rows:
                profile = dict(row)
                distance_km = haversine(profile.get("latitude"), profile.get("longitude"))
                if distance_km is not None and distance_km > prefs["max_distance_km"]:
                    continue
                profile["distance_km"] = distance_km
                filtered.append(profile)
                if len(filtered) == limit:
                    break

            if not filtered:
                return {"success": True, "data": []}

            # Batch load all photos in a single query
            profile_ids = [p["profile_id"] for p in filtered]
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
                    "profile_id": p["profile_id"],
                    "user_id": p["user_id"],
                    "name": p["name"],
                    "bio": p["bio"],
                    "age": p["age"],
                    "gender": p["gender"],
                    "distance_km": p["distance_km"],
                    "photos": photos_by_profile.get(p["profile_id"], []),
                }
                for p in filtered
            ]

            ranked = await self.compatibility.rank(dict(viewer), results)
            return {"success": True, "data": ranked}

        except Exception as e:
            self.logger.error(f"Error generating discovery feed: {e}")
            return {"success": False, "error": str(e)}
