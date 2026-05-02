"""
Transmitter Database

Responsibilities:
- store transmitter metadata for satellites
- load/save local cache
- update from SatNOGS API
- provide lookup by NORAD ID or transmitter UUID
"""

import json
import time
from pathlib import Path

from pydantic import BaseModel, Field


class Transmitter(BaseModel):
    uuid: str
    norad_id: int = Field(..., alias="norad")
    description: str
    frequency: float  # Hz
    mode: str  # e.g. "FM", "BPSK", "FSK"
    bandwidth: float | None = None
    updated: float  # UNIX timestamp


class TransmitterDB:
    """
    High-level transmitter database with local caching and remote update support.
    """

    def __init__(
        self,
        cache_path: Path = Path("data/transmitters.json"),
        max_age_hours: float = 24.0,
    ):
        self.cache_path = cache_path
        self.max_age = max_age_hours * 3600
        self.transmitters: dict[str, Transmitter] = {}  # uuid → Transmitter

        self._load_cache()

    def _load_cache(self):
        if not self.cache_path.exists():
            self.transmitters = {}
            return

        try:
            with open(self.cache_path, "r") as f:
                raw = json.load(f)
                self.transmitters = {
                    uuid: Transmitter(**entry) for uuid, entry in raw.items()
                }
        except Exception:
            self.transmitters = {}

    def _save_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(
                {
                    uuid: tx.model_dump(by_alias=True)
                    for uuid, tx in self.transmitters.items()
                },
                f,
                indent=4,
            )

    def get_by_uuid(self, uuid: str) -> Transmitter | None:
        return self.transmitters.get(uuid)

    def get_by_norad(self, norad_id: int) -> list[Transmitter]:
        return [tx for tx in self.transmitters.values() if tx.norad_id == norad_id]

    def is_fresh(self, tx: Transmitter) -> bool:
        return (time.time() - tx.updated) < self.max_age

    async def update_from_satnogs(self, norad_id: int, client) -> list[Transmitter]:
        """
        Fetch transmitter metadata from SatNOGS.

        `client` must implement:
            await client.get_transmitters(norad_id) -> list of dicts
        """
        try:
            data = await client.get_transmitters(norad_id)
            if not data:
                return []

            updated_list = []

            for entry in data:
                uuid = entry.get("uuid")
                if not uuid:
                    continue

                tx = Transmitter(
                    uuid=uuid,
                    norad=norad_id,
                    description=entry.get("description", "Unknown"),
                    frequency=float(entry.get("downlink_low", 0)),
                    mode=entry.get("mode", "Unknown"),
                    bandwidth=entry.get("bandwidth"),
                    updated=time.time(),
                )

                self.transmitters[uuid] = tx
                updated_list.append(tx)

            self._save_cache()
            return updated_list

        except Exception:
            return []
