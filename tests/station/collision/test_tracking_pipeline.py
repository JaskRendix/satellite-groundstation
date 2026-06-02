from datetime import datetime, timedelta, timezone

import pytest

from groundstation.station.collision.planner import PlannedTrack
from groundstation.station.collision.simulator import SimulationResult
from groundstation.station.collision.tracking_pipeline import TrackingPipeline
from groundstation.station.tracking.predictor import PassEvent, TrackPoint


class FakePredictor:
    """Predictor that returns a predefined track."""

    def __init__(self, track):
        self.track = track

    def generate_track(self, tle_text):
        if tle_text == "EMPTY":
            return [], None
        event = PassEvent(
            aos_time=self.track[0].time,
            aos_az=self.track[0].az,
            max_time=self.track[len(self.track) // 2].time,
            max_az=self.track[len(self.track) // 2].az,
            max_el=self.track[len(self.track) // 2].el,
            los_time=self.track[-1].time,
            los_az=self.track[-1].az,
        )
        return self.track, event


class FakeTLEManager:
    """TLE manager that returns a fixed TLE string."""

    def __init__(self, tle="FAKE"):
        self.tle = tle

    def get_tle_text(self, norad_id):
        return self.tle


@pytest.fixture
def rotator_cfg():
    return {
        "azimuth": {"min_deg": 0, "max_deg": 360},
        "elevation": {"min_deg": 0, "max_deg": 180},
    }


def make_track(n=5, az=100, el=45):
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [
        TrackPoint(time=base + timedelta(seconds=i * 5), az=az, el=el, range_km=500)
        for i in range(n)
    ]


def test_no_tle(rotator_cfg):
    predictor = FakePredictor(make_track())
    tle_mgr = FakeTLEManager(tle=None)

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={"enabled": True},
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert raw == []
    assert event is None
    assert isinstance(planned, PlannedTrack)
    assert "No TLE available" in planned.warnings


def test_empty_track(rotator_cfg):
    predictor = FakePredictor([])
    tle_mgr = FakeTLEManager(tle="EMPTY")

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={"enabled": True},
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert raw == []
    assert event is None
    assert "No valid pass" in planned.warnings


def test_collision_disabled(rotator_cfg):
    track = make_track()
    predictor = FakePredictor(track)
    tle_mgr = FakeTLEManager()

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={"enabled": False},
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert raw == track
    assert planned.points == track
    assert planned.dropped_segments == []


def test_strict_mode_drops_unsafe(monkeypatch, rotator_cfg):
    track = make_track()

    predictor = FakePredictor(track)
    tle_mgr = FakeTLEManager()

    # Force simulator to mark all points unsafe
    def fake_simulate(self, track):
        return SimulationResult(
            safe_points=[],
            unsafe_points=[(tp, ["boom_mast_collision"]) for tp in track],
        )

    monkeypatch.setattr(
        "groundstation.station.collision.simulator.CollisionSimulator.simulate",
        fake_simulate,
    )

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={"enabled": True, "mode": "strict"},
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert planned.points == []
    assert len(planned.dropped_segments) == 1
    assert "dropped" in planned.warnings[0].lower()


def test_clamp_mode(monkeypatch, rotator_cfg):
    track = make_track(az=10, el=-5)  # invalid elevation

    predictor = FakePredictor(track)
    tle_mgr = FakeTLEManager()

    # Fake simulator: mark all points unsafe
    def fake_simulate(self, track):
        return SimulationResult(
            safe_points=[],
            unsafe_points=[(tp, [{"type": "elevation_limit"}]) for tp in track],
        )

    monkeypatch.setattr(
        "groundstation.station.collision.simulator.CollisionSimulator.simulate",
        fake_simulate,
    )

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={"enabled": True, "mode": "clamp"},
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert len(planned.points) == len(track)
    assert all(p.el >= 0 for p in planned.points)  # clamped to min elevation


@pytest.mark.parametrize("az", [10, 350])
def test_forbidden_azimuth(monkeypatch, rotator_cfg, az):
    track = make_track(az=az, el=45)

    predictor = FakePredictor(track)
    tle_mgr = FakeTLEManager()

    # Fake simulator: mark all points unsafe due to forbidden azimuth
    def fake_simulate(self, track):
        return SimulationResult(
            safe_points=[],
            unsafe_points=[
                (
                    tp,
                    [
                        {
                            "type": "forbidden_azimuth",
                            "details": {"start_deg": 0, "end_deg": 20},
                        }
                    ],
                )
                for tp in track
            ],
        )

    monkeypatch.setattr(
        "groundstation.station.collision.simulator.CollisionSimulator.simulate",
        fake_simulate,
    )

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={
            "enabled": True,
            "mode": "clamp",
            "forbidden_azimuth_sectors": [{"start_deg": 0, "end_deg": 20}],
        },
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert len(planned.points) == len(track)
    assert all(p.az < 0 or p.az > 20 for p in planned.points)


def test_ground_clearance(monkeypatch, rotator_cfg):
    track = make_track(el=0)

    predictor = FakePredictor(track)
    tle_mgr = FakeTLEManager()

    def fake_simulate(self, track):
        return SimulationResult(
            safe_points=[],
            unsafe_points=[(tp, [{"type": "ground_clearance_vhf"}]) for tp in track],
        )

    monkeypatch.setattr(
        "groundstation.station.collision.simulator.CollisionSimulator.simulate",
        fake_simulate,
    )

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={"enabled": True, "mode": "clamp"},
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert all(p.el >= 5 for p in planned.points)  # min elevation for clearance


def test_mast_collision(monkeypatch, rotator_cfg):
    track = make_track(el=10)

    predictor = FakePredictor(track)
    tle_mgr = FakeTLEManager()

    def fake_simulate(self, track):
        return SimulationResult(
            safe_points=[],
            unsafe_points=[(tp, [{"type": "boom_mast_collision_vhf"}]) for tp in track],
        )

    monkeypatch.setattr(
        "groundstation.station.collision.simulator.CollisionSimulator.simulate",
        fake_simulate,
    )

    pipeline = TrackingPipeline(
        predictor=predictor,
        tle_manager=tle_mgr,
        rotator_cfg=rotator_cfg,
        collision_cfg={"enabled": True, "mode": "clamp"},
    )

    raw, event, planned = pipeline.compute_safe_track(25544)

    assert all(p.el > 10 for p in planned.points)
