import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from groundstation.station.tracking.tle_manager import TleEntry, TleManager


def make_entry(norad=1001, age_seconds=0):
    """Create a TleEntry with a controlled timestamp."""
    return TleEntry(
        name="TESTSAT",
        norad=norad,
        tle1="1 00000A",
        tle2="2 00000B",
        updated=time.time() - age_seconds,
    )


@pytest.fixture
def tmp_cache(tmp_path):
    """Return a temporary cache path."""
    return tmp_path / "tle_cache.json"


@pytest.fixture
def manager(tmp_cache):
    """Fresh TleManager with empty cache."""
    return TleManager(cache_path=tmp_cache, max_age_hours=1)


def test_load_cache_empty_file(manager, tmp_cache):
    # No file exists → empty dict
    assert manager.tles == {}


def test_load_cache_valid(tmp_cache):
    raw = {
        "1001": {
            "name": "SAT",
            "norad": 1001,
            "tle1": "1 A",
            "tle2": "2 B",
            "updated": time.time(),
        }
    }
    tmp_cache.write_text(json.dumps(raw))

    m = TleManager(cache_path=tmp_cache)
    assert 1001 in m.tles
    assert m.tles[1001].name == "SAT"


def test_load_cache_invalid_json(tmp_cache):
    tmp_cache.write_text("{not valid json")

    m = TleManager(cache_path=tmp_cache)
    assert m.tles == {}


def test_get_tle_fresh(manager):
    manager.tles[1001] = make_entry(age_seconds=0)
    assert manager.get_tle(1001) is not None


def test_get_tle_expired(manager):
    manager.tles[1001] = make_entry(age_seconds=999999)
    assert manager.get_tle(1001) is None


def test_get_tle_missing(manager):
    assert manager.get_tle(9999) is None


def test_get_tle_text_success(manager):
    manager.tles[1001] = make_entry()
    txt = manager.get_tle_text(1001)
    assert txt == "1 00000A\n2 00000B"


def test_get_tle_text_none(manager):
    assert manager.get_tle_text(1001) is None


def test_update_tle_writes_cache(manager, tmp_cache):
    manager.update_tle(1001, "SAT", "1 A", "2 B")

    assert 1001 in manager.tles
    assert tmp_cache.exists()

    raw = json.loads(tmp_cache.read_text())
    assert "1001" in raw
    assert raw["1001"]["name"] == "SAT"


@pytest.mark.asyncio
async def test_fetch_from_remote_success(manager):
    client = MagicMock()
    client.get_tle = AsyncMock(
        return_value={
            "name": "SAT",
            "tle1": "1 A",
            "tle2": "2 B",
        }
    )

    entry = await manager.fetch_from_remote(1001, client)

    assert isinstance(entry, TleEntry)
    assert entry.name == "SAT"
    assert 1001 in manager.tles


@pytest.mark.asyncio
async def test_fetch_from_remote_returns_none(manager):
    client = MagicMock()
    client.get_tle = AsyncMock(return_value=None)

    entry = await manager.fetch_from_remote(1001, client)
    assert entry is None


@pytest.mark.asyncio
async def test_fetch_from_remote_exception(manager):
    client = MagicMock()
    client.get_tle = AsyncMock(side_effect=Exception("boom"))

    entry = await manager.fetch_from_remote(1001, client)
    assert entry is None
