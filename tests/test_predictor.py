from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from groundstation.station.tracking.predictor import PassEvent, TrackPoint


class FakeEvent:
    def __init__(self, info):
        self.info = info


class FakeOrb:
    def __init__(self, date, theta=0.0, phi=0.0, r=700000.0, event=None):
        self.date = date
        self.theta = theta
        self.phi = phi
        self.r = r
        self.event = event


def make_dt(offset_s):
    base = datetime(2025, 1, 1, 12, 0, 0)
    dt = base + timedelta(seconds=offset_s)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


@pytest.fixture
def predictor():
    with (
        patch("groundstation.station.tracking.predictor.create_station") as cs,
        patch("groundstation.station.tracking.predictor.Tle") as mock_tle,
    ):

        from groundstation.station.tracking.predictor import Predictor

        station = MagicMock()
        cs.return_value = station

        fake_tle = MagicMock()
        fake_tle.orbit.return_value = MagicMock()
        mock_tle.return_value = fake_tle

        p = Predictor(46.0, 8.0, 300.0, min_max_elevation=10.0)
        yield p


def test_to_utc_parses_datetime(predictor):
    dt = predictor._to_utc("2025-01-01T12:00:00.000000")
    assert dt.year == 2025
    assert dt.tzinfo is not None
    assert dt.tzinfo.utcoffset(dt) == timedelta(0)


def test_predict_first_pass_success(predictor):
    seq = [
        FakeOrb(make_dt(0), theta=-1.0, phi=0.0, event=FakeEvent("AOS")),
        FakeOrb(make_dt(10), theta=-2.0, phi=0.3, event=FakeEvent("MAX")),
        FakeOrb(make_dt(20), theta=-3.0, phi=0.1, event=FakeEvent("LOS")),
    ]

    predictor.station.visibility = MagicMock(return_value=seq)

    evt = predictor.predict_first_pass("dummy")

    assert isinstance(evt, PassEvent)
    assert evt.max_el > 10.0
    assert evt.aos_az != evt.los_az


def test_predict_first_pass_rejects_low_max(predictor):
    seq = [
        FakeOrb(make_dt(0), theta=-1.0, phi=0.0, event=FakeEvent("AOS")),
        FakeOrb(make_dt(10), theta=-2.0, phi=0.05, event=FakeEvent("MAX")),
        FakeOrb(make_dt(20), theta=-3.0, phi=0.1, event=FakeEvent("LOS")),
    ]

    predictor.station.visibility = MagicMock(return_value=seq)

    evt = predictor.predict_first_pass("dummy")
    assert evt is None


def test_generate_track_success(predictor):
    seq = [
        FakeOrb(make_dt(0), theta=-1.0, phi=0.0, r=700000, event=FakeEvent("AOS")),
        FakeOrb(make_dt(5), theta=-1.5, phi=0.2, r=705000, event=None),
        FakeOrb(make_dt(10), theta=-2.0, phi=0.3, r=710000, event=FakeEvent("MAX")),
        FakeOrb(make_dt(15), theta=-2.5, phi=0.1, r=720000, event=FakeEvent("LOS")),
    ]

    predictor.station.visibility = MagicMock(return_value=seq)

    track, evt = predictor.generate_track("dummy")

    assert len(track) == 4
    assert isinstance(track[0], TrackPoint)
    assert isinstance(evt, PassEvent)
    assert evt.max_el > 10.0


def test_generate_track_clears_on_invalid_pass(predictor):
    seq = [
        FakeOrb(make_dt(0), theta=-1.0, phi=0.0, event=FakeEvent("AOS")),
        FakeOrb(make_dt(10), theta=-2.0, phi=0.05, event=FakeEvent("MAX")),
        FakeOrb(make_dt(20), theta=-3.0, phi=0.1, event=FakeEvent("LOS")),
    ]

    predictor.station.visibility = MagicMock(return_value=seq)

    track, evt = predictor.generate_track("dummy")

    assert track == []
    assert evt is None
