"""
Async SatNOGS API client.

Responsibilities:
- fetch TLEs
- fetch transmitter metadata
- fetch satellite info
- provide clean async API for TleManager and Scheduler
"""

from typing import Any

import aiohttp


class SatnogsClient:
    """
    Async client for SatNOGS API.

    API docs:
    https://db.satnogs.org/api/
    """

    BASE_URL = "https://db.satnogs.org/api"

    def __init__(self, api_token: str | None = None, timeout: int = 10):
        self.api_token = api_token
        self.timeout = timeout

    async def _get(self, endpoint: str, params: dict[str, Any] = None) -> Any | None:
        url = f"{self.BASE_URL}/{endpoint}"

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.json()
        except Exception:
            return None

    async def get_tle(self, norad_id: int) -> dict[str, str] | None:
        """
        Fetch TLE for a given NORAD ID.

        Returns:
            {
                "name": "...",
                "tle1": "...",
                "tle2": "..."
            }
        """
        data = await self._get("tle/", params={"norad_cat_id": norad_id})

        if not data or len(data) == 0:
            return None

        tle = data[0]  # SatNOGS returns a list

        return {
            "name": tle.get("satellite", "Unknown"),
            "tle1": tle.get("tle1", ""),
            "tle2": tle.get("tle2", ""),
        }

    async def get_transmitters(self, norad_id: int) -> Any | None:
        """
        Fetch transmitter metadata for a satellite.
        """
        return await self._get("transmitters/", params={"norad_cat_id": norad_id})

    async def get_satellite_info(self, norad_id: int) -> Any | None:
        """
        Fetch general satellite info.
        """
        return await self._get("satellites/", params={"norad_cat_id": norad_id})
