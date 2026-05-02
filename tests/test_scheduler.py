import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from groundstation.station.tracking.predictor import PassEvent
from groundstation.station.tracking.scheduler import ScheduledPass, Scheduler


def make_event(offset_aos=10, offset_los=20):
    """Create a fake PassEvent with AOS/LOS offsets from now."""
    now = datetime.now(timezone.utc)
    return PassEvent(
        aos_time=now + timedelta(seconds=offset_aos),
        aos_az=100.0,
        max_time=now + timedelta(seconds=offset_aos + 5),
        max_az=120.0,
        max_el=45.0,
        los_time=now + timedelta(seconds=offset_los),
        los_az=200.0,
    )


@pytest.fixture
def predictor():
    p = MagicMock()
    p.predict_first_pass = MagicMock()
    return p


@pytest.fixture
def tle_manager():
    tm = MagicMock()
    tm.get_tle_text = MagicMock()
    return tm


@pytest.fixture
def scheduler(predictor, tle_manager):
    tracked = {"SAT1": 1001, "SAT2": 1002}
    return Scheduler(predictor, tle_manager, tracked)


def test_predict_single_success(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.return_value = "TLE TEXT"
    predictor.predict_first_pass.return_value = make_event()

    sp = scheduler._predict_single("SAT1", 1001)

    assert isinstance(sp, ScheduledPass)
    assert sp.name == "SAT1"
    assert sp.norad_id == 1001


def test_predict_single_no_tle(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.return_value = None
    sp = scheduler._predict_single("SAT1", 1001)
    assert sp is None


def test_predict_single_no_pass(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.return_value = "TLE"
    predictor.predict_first_pass.return_value = None
    sp = scheduler._predict_single("SAT1", 1001)
    assert sp is None


def test_predict_all_sorted_by_aos(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.return_value = "TLE"

    evt1 = make_event(offset_aos=30)
    evt2 = make_event(offset_aos=10)

    predictor.predict_first_pass.side_effect = [evt1, evt2]

    results = scheduler.predict_all()

    assert len(results) == 2
    assert results[0].event.aos_time < results[1].event.aos_time


def test_predict_all_filters_none(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.side_effect = ["TLE", None]
    predictor.predict_first_pass.return_value = make_event()

    results = scheduler.predict_all()

    assert len(results) == 1
    assert results[0].name == "SAT1"


def test_next_pass_returns_future_pass(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.return_value = "TLE"
    predictor.predict_first_pass.return_value = make_event(offset_aos=5)

    nxt = scheduler.next_pass()
    assert isinstance(nxt, ScheduledPass)


def test_next_pass_none_if_all_past(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.return_value = "TLE"

    past_evt = make_event(offset_aos=-10)
    predictor.predict_first_pass.return_value = past_evt

    nxt = scheduler.next_pass()
    assert nxt is None


@pytest.mark.asyncio
async def test_run_scheduler_triggers_callbacks(scheduler, predictor, tle_manager):
    tle_manager.get_tle_text.return_value = "TLE"

    # AOS very soon, LOS shortly after
    evt = make_event(offset_aos=0.01, offset_los=0.02)
    predictor.predict_first_pass.return_value = evt

    start_cb = MagicMock()
    end_cb = MagicMock()

    # Run scheduler in the background and cancel after a short time
    task = asyncio.create_task(
        scheduler.run_scheduler(start_cb, end_cb, poll_interval=999)
    )

    # Give it a bit of real time to hit AOS and LOS once
    await asyncio.sleep(0.05)

    # Cancel the infinite loop
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify callbacks were triggered
    start_cb.assert_called_once()
    end_cb.assert_called_once()
