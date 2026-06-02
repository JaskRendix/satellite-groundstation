from datetime import datetime, timedelta, timezone

from groundstation.station.collision.geometry import (
    DefaultCollisionConfig,
    GeometryModel,
)
from groundstation.station.collision.simulator import (
    CollisionSimulator,
    SimulationResult,
)
from groundstation.station.tracking.predictor import TrackPoint


def tp(t=0, az=100, el=45):
    """Create a TrackPoint at time offset t seconds."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return TrackPoint(
        time=base + timedelta(seconds=t),
        az=az,
        el=el,
        range_km=500,
    )


class FakeGeometry:
    """GeometryModel mock that returns a constant pose."""

    def __init__(self):
        self.calls = []

    def pose(self, az, el):
        self.calls.append((az, el))
        # Return a dummy pose-like object
        return "POSE"


class FakeChecker:
    """ConstraintChecker mock that returns predefined violations."""

    def __init__(self, violations_map):
        self.violations_map = violations_map
        self.calls = []

    def check(self, tp, pose):
        self.calls.append((tp, pose))
        return self.violations_map.get(tp.time, [])


def test_simulator_all_safe():
    track = [tp(0), tp(5), tp(10)]

    geom = FakeGeometry()
    checker = FakeChecker(violations_map={})

    sim = CollisionSimulator(geom, checker)
    result = sim.simulate(track)

    assert isinstance(result, SimulationResult)
    assert result.safe_points == track
    assert result.unsafe_points == []
    assert len(geom.calls) == 3
    assert len(checker.calls) == 3


def test_simulator_all_unsafe():
    track = [tp(0), tp(5)]

    violations = {
        track[0].time: ["boom_mast_collision"],
        track[1].time: ["ground_clearance_vhf"],
    }

    geom = FakeGeometry()
    checker = FakeChecker(violations_map=violations)

    sim = CollisionSimulator(geom, checker)
    result = sim.simulate(track)

    assert result.safe_points == []
    assert len(result.unsafe_points) == 2

    # Check ordering
    assert result.unsafe_points[0][0] == track[0]
    assert result.unsafe_points[1][0] == track[1]


def test_simulator_mixed_safe_unsafe():
    track = [tp(0), tp(5), tp(10)]

    violations = {
        track[1].time: ["elevation_limit"],
    }

    geom = FakeGeometry()
    checker = FakeChecker(violations_map=violations)

    sim = CollisionSimulator(geom, checker)
    result = sim.simulate(track)

    assert result.safe_points == [track[0], track[2]]
    assert len(result.unsafe_points) == 1
    assert result.unsafe_points[0][0] == track[1]


def test_simulator_empty_track():
    geom = FakeGeometry()
    checker = FakeChecker(violations_map={})

    sim = CollisionSimulator(geom, checker)
    result = sim.simulate([])

    assert result.safe_points == []
    assert result.unsafe_points == []
    assert geom.calls == []
    assert checker.calls == []


def test_simulator_multiple_violations_per_point():
    track = [tp(0)]

    violations = {
        track[0].time: ["boom_mast_collision", "ground_clearance_vhf"],
    }

    geom = FakeGeometry()
    checker = FakeChecker(violations_map=violations)

    sim = CollisionSimulator(geom, checker)
    result = sim.simulate(track)

    assert len(result.unsafe_points) == 1
    tp0, vlist = result.unsafe_points[0]
    assert tp0 == track[0]
    assert vlist == ["boom_mast_collision", "ground_clearance_vhf"]


def test_simulator_with_real_geometry_and_checker():
    # Real geometry
    geom = GeometryModel(DefaultCollisionConfig())

    # Checker that flags elevation < 0 as unsafe
    class SimpleChecker:
        def check(self, tp, pose):
            return ["elevation_limit"] if tp.el < 0 else []

    checker = SimpleChecker()

    track = [tp(0, el=10), tp(5, el=-5), tp(10, el=20)]

    sim = CollisionSimulator(geom, checker)
    result = sim.simulate(track)

    assert result.safe_points == [track[0], track[2]]
    assert len(result.unsafe_points) == 1
    assert result.unsafe_points[0][0] == track[1]
