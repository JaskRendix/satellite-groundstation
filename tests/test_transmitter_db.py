import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from groundstation.station.tracking.transmitter_db import Transmitter, TransmitterDB


def make_tx(
    uuid="abc-123",
    norad=1001,
    freq=437500000,
    mode="FM",
    bandwidth=None,
    age_seconds=0,
):
    return Transmitter(
        uuid=uuid,
        norad=norad,
        description="Test TX",
        frequency=freq,
        mode=mode,
        bandwidth=bandwidth,
        updated=time.time() - age_seconds,
    )


@pytest.fixture
def tmp_cache(tmp_path):
    return tmp_path / "transmitters.json"


@pytest.fixture
def db(tmp_cache):
    return TransmitterDB(cache_path=tmp_cache, max_age_hours=1)


def test_load_cache_missing_file(db):
    assert db.transmitters == {}


def test_load_cache_valid(tmp_cache):
    raw = {
        "abc-123": {
            "uuid": "abc-123",
            "norad": 1001,
            "description": "TX",
            "frequency": 437e6,
            "mode": "FM",
            "bandwidth": None,
            "updated": time.time(),
        }
    }
    tmp_cache.write_text(json.dumps(raw))

    db = TransmitterDB(cache_path=tmp_cache)
    assert "abc-123" in db.transmitters
    assert db.transmitters["abc-123"].mode == "FM"


def test_load_cache_invalid_json(tmp_cache):
    tmp_cache.write_text("{not valid json")

    db = TransmitterDB(cache_path=tmp_cache)
    assert db.transmitters == {}


def test_get_by_uuid(db):
    tx = make_tx()
    db.transmitters[tx.uuid] = tx

    assert db.get_by_uuid(tx.uuid) is tx
    assert db.get_by_uuid("missing") is None


def test_get_by_norad(db):
    tx1 = make_tx(uuid="u1", norad=1001)
    tx2 = make_tx(uuid="u2", norad=1001)
    tx3 = make_tx(uuid="u3", norad=9999)

    db.transmitters = {t.uuid: t for t in [tx1, tx2, tx3]}

    result = db.get_by_norad(1001)
    assert len(result) == 2
    assert tx1 in result and tx2 in result


def test_is_fresh_true(db):
    tx = make_tx(age_seconds=0)
    assert db.is_fresh(tx)


def test_is_fresh_false(db):
    tx = make_tx(age_seconds=db.max_age + 10)
    assert not db.is_fresh(tx)


def test_save_cache_writes_file(db, tmp_cache):
    tx = make_tx()
    db.transmitters[tx.uuid] = tx

    db._save_cache()

    assert tmp_cache.exists()
    raw = json.loads(tmp_cache.read_text())
    assert tx.uuid in raw
    assert raw[tx.uuid]["mode"] == tx.mode


@pytest.mark.asyncio
async def test_update_from_satnogs_success(db, tmp_cache):
    client = MagicMock()
    client.get_transmitters = AsyncMock(
        return_value=[
            {
                "uuid": "abc-123",
                "description": "Downlink",
                "downlink_low": 437500000,
                "mode": "FM",
                "bandwidth": 20000,
            }
        ]
    )

    updated = await db.update_from_satnogs(1001, client)

    assert len(updated) == 1
    tx = updated[0]
    assert tx.uuid == "abc-123"
    assert tx.norad_id == 1001
    assert tx.frequency == 437500000
    assert "abc-123" in db.transmitters
    assert tmp_cache.exists()


@pytest.mark.asyncio
async def test_update_from_satnogs_empty(db):
    client = MagicMock()
    client.get_transmitters = AsyncMock(return_value=[])

    updated = await db.update_from_satnogs(1001, client)
    assert updated == []


@pytest.mark.asyncio
async def test_update_from_satnogs_missing_uuid(db):
    client = MagicMock()
    client.get_transmitters = AsyncMock(
        return_value=[{"description": "No UUID", "downlink_low": 437e6}]
    )

    updated = await db.update_from_satnogs(1001, client)
    assert updated == []
    assert db.transmitters == {}


@pytest.mark.asyncio
async def test_update_from_satnogs_exception(db):
    client = MagicMock()
    client.get_transmitters = AsyncMock(side_effect=Exception("boom"))

    updated = await db.update_from_satnogs(1001, client)
    assert updated == []
