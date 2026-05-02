from unittest.mock import patch

import pytest

from groundstation.station.tracking.satnogs_client import SatnogsClient

pytestmark = pytest.mark.asyncio


class FakeResponse:
    def __init__(self, status=200, json_data=None):
        self.status = status
        self._json_data = json_data

    async def json(self):
        return self._json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeSession:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    # sync, not async
    def get(self, url, params=None, headers=None):
        return self._response


async def test_get_success():
    response = FakeResponse(status=200, json_data={"ok": True})

    # IMPORTANT: patch ClientSession as a CLASS, not an instance
    with patch("aiohttp.ClientSession", return_value=FakeSession(response)):
        client = SatnogsClient(api_token="ABC")
        data = await client._get("tle/", params={"norad_cat_id": 123})

    assert data == {"ok": True}


async def test_get_non_200_returns_none():
    response = FakeResponse(status=404, json_data=None)

    with patch("aiohttp.ClientSession", return_value=FakeSession(response)):
        client = SatnogsClient()
        data = await client._get("tle/", params={"norad_cat_id": 123})

    assert data is None


async def test_get_exception_returns_none():
    with patch("aiohttp.ClientSession", side_effect=Exception("boom")):
        client = SatnogsClient()
        data = await client._get("tle/")

    assert data is None


async def test_get_tle_success():
    fake_data = [
        {
            "satellite": "TESTSAT",
            "tle1": "1 00000A",
            "tle2": "2 00000B",
        }
    ]

    response = FakeResponse(status=200, json_data=fake_data)

    with patch("aiohttp.ClientSession", return_value=FakeSession(response)):
        client = SatnogsClient()
        tle = await client.get_tle(123)

    assert tle == {
        "name": "TESTSAT",
        "tle1": "1 00000A",
        "tle2": "2 00000B",
    }


async def test_get_tle_empty_returns_none():
    response = FakeResponse(status=200, json_data=[])

    with patch("aiohttp.ClientSession", return_value=FakeSession(response)):
        client = SatnogsClient()
        tle = await client.get_tle(123)

    assert tle is None


async def test_get_transmitters_success():
    fake_data = [{"freq": 437.5}]

    response = FakeResponse(status=200, json_data=fake_data)

    with patch("aiohttp.ClientSession", return_value=FakeSession(response)):
        client = SatnogsClient()
        tx = await client.get_transmitters(123)

    assert tx == fake_data


async def test_get_satellite_info_success():
    fake_data = [{"name": "SAT-1"}]

    response = FakeResponse(status=200, json_data=fake_data)

    with patch("aiohttp.ClientSession", return_value=FakeSession(response)):
        client = SatnogsClient()
        info = await client.get_satellite_info(123)

    assert info == fake_data
