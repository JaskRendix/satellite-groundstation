"""
Modern TLE Manager

Responsibilities:
- load TLEs from local cache
- fetch updated TLEs from remote sources (e.g., SatNOGS)
- validate and store TLEs
- provide lookup by NORAD ID or satellite name
"""

import json
import time
from pathlib import Path

from pydantic import BaseModel, Field


class TleEntry(BaseModel):
    name: str
    norad_id: int = Field(..., alias="norad")
    tle1: str
    tle2: str
    updated: float  # UNIX timestamp


class TleManager:
    """
    High-level TLE manager with local caching and remote update support.
    """

    def __init__(
        self,
        cache_path: Path = Path("data/tle_cache.json"),
        max_age_hours: float = 12.0,
    ):
        self.cache_path = cache_path
        self.max_age = max_age_hours * 3600
        self.tles: dict[int, TleEntry] = {}

        self._load_cache()

    def _load_cache(self):
        if not self.cache_path.exists():
            self.tles = {}
            return

        try:
            with open(self.cache_path, "r") as f:
                raw = json.load(f)
                self.tles = {int(k): TleEntry(**v) for k, v in raw.items()}
        except Exception:
            self.tles = {}

    def _save_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(
                {k: v.model_dump(by_alias=True) for k, v in self.tles.items()},
                f,
                indent=4,
            )

    def get_tle(self, norad_id: int) -> TleEntry | None:
        """
        Return TLE from cache if fresh enough.
        """
        entry = self.tles.get(norad_id)
        if not entry:
            return None

        if time.time() - entry.updated > self.max_age:
            return None

        return entry

    def get_tle_text(self, norad_id: int) -> str | None:
        """
        Return TLE as a combined 2-line string.
        """
        entry = self.get_tle(norad_id)
        if not entry:
            return None
        return f"{entry.tle1}\n{entry.tle2}"

    def update_tle(
        self,
        norad_id: int,
        name: str,
        tle1: str,
        tle2: str,
    ):
        """
        Insert or update a TLE entry.
        """
        self.tles[norad_id] = TleEntry(
            name=name,
            norad=norad_id,
            tle1=tle1,
            tle2=tle2,
            updated=time.time(),
        )
        self._save_cache()

    async def fetch_from_remote(self, norad_id: int, client) -> TleEntry | None:
        """
        Fetch TLE from remote source (e.g., SatNOGS client).

        `client` must implement:
            await client.get_tle(norad_id) -> dict with keys:
                name, tle1, tle2
        """
        try:
            data = await client.get_tle(norad_id)
            if not data:
                return None

            self.update_tle(
                norad_id=norad_id,
                name=data["name"],
                tle1=data["tle1"],
                tle2=data["tle2"],
            )

            return self.tles[norad_id]

        except Exception:
            return None
