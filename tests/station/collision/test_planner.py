from datetime import datetime, timedelta, timezone

from groundstation.station.collision.constraints import ConstraintConfig, Violation
from groundstation.station.collision.planner import CollisionPlanner
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


def cfg():
    """Minimal constraint config."""
    return ConstraintConfig(
        az_min=0,
        az_max=360,
        el_min=0,
        el_max=180,
        clearance_min_m=0.3,
        forbidden_azimuth_sectors=[],
    )


def test_strict_mode_drops_all_unsafe():
    planner = CollisionPlanner(cfg(), mode="strict")

    safe_points = []
    unsafe_points = [
        (tp(0), [Violation(tp(0).time, 100, 45, "boom_mast_collision_vhf", {})])
    ]

    sim = type("Sim", (), {"safe_points": safe_points, "unsafe_points": unsafe_points})

    planned = planner.plan(sim)

    assert planned.points == []
    assert len(planned.dropped_segments) == 1
    assert "dropped" in planned.warnings[0].lower()


def test_strict_mode_keeps_safe_points_only():
    planner = CollisionPlanner(cfg(), mode="strict")

    safe_points = [tp(0), tp(5)]
    unsafe_points = [(tp(10), [{"type": "elevation_limit"}])]

    sim = type("Sim", (), {"safe_points": safe_points, "unsafe_points": unsafe_points})

    planned = planner.plan(sim)

    assert planned.points == safe_points
    assert len(planned.dropped_segments) == 1


def test_clamp_mode_keeps_timeline():
    planner = CollisionPlanner(cfg(), mode="clamp")

    safe_points = [tp(0)]
    unsafe_points = [(tp(5), [{"type": "elevation_limit"}])]

    sim = type("Sim", (), {"safe_points": safe_points, "unsafe_points": unsafe_points})

    planned = planner.plan(sim)

    assert len(planned.points) == 2
    assert planned.points[0].time < planned.points[1].time


def test_clamp_elevation_limit():
    planner = CollisionPlanner(cfg(), mode="clamp")

    unsafe = tp(0, az=100, el=-10)
    sim = type(
        "Sim",
        (),
        {"safe_points": [], "unsafe_points": [(unsafe, [{"type": "elevation_limit"}])]},
    )

    planned = planner.plan(sim)

    assert planned.points[0].el == 0  # clamped to el_min


def test_clamp_azimuth_limit():
    planner = CollisionPlanner(cfg(), mode="clamp")

    unsafe = tp(0, az=999, el=45)
    sim = type(
        "Sim",
        (),
        {"safe_points": [], "unsafe_points": [(unsafe, [{"type": "azimuth_limit"}])]},
    )

    planned = planner.plan(sim)

    assert planned.points[0].az == 360  # clamped to az_max


def test_clamp_ground_clearance():
    planner = CollisionPlanner(cfg(), mode="clamp")

    unsafe = tp(0, az=100, el=0)
    sim = type(
        "Sim",
        (),
        {
            "safe_points": [],
            "unsafe_points": [(unsafe, [{"type": "ground_clearance_vhf"}])],
        },
    )

    planned = planner.plan(sim)

    assert planned.points[0].el >= 5  # bumped to minimum safe elevation


def test_clamp_forbidden_azimuth():
    c = cfg()
    c.forbidden_azimuth_sectors = [{"start_deg": 90, "end_deg": 110}]

    planner = CollisionPlanner(c, mode="clamp")

    unsafe = tp(0, az=100, el=45)
    sim = type(
        "Sim",
        (),
        {
            "safe_points": [],
            "unsafe_points": [
                (
                    unsafe,
                    [
                        {
                            "type": "forbidden_azimuth",
                            "details": c.forbidden_azimuth_sectors[0],
                        }
                    ],
                )
            ],
        },
    )

    planned = planner.plan(sim)

    assert planned.points[0].az < 90 or planned.points[0].az > 110


def test_clamp_forbidden_azimuth_wraparound():
    c = cfg()
    c.forbidden_azimuth_sectors = [{"start_deg": 350, "end_deg": 20}]

    planner = CollisionPlanner(c, mode="clamp")

    unsafe = tp(0, az=355, el=45)
    sim = type(
        "Sim",
        (),
        {
            "safe_points": [],
            "unsafe_points": [
                (
                    unsafe,
                    [
                        {
                            "type": "forbidden_azimuth",
                            "details": c.forbidden_azimuth_sectors[0],
                        }
                    ],
                )
            ],
        },
    )

    planned = planner.plan(sim)

    assert not (350 <= planned.points[0].az <= 360 or 0 <= planned.points[0].az <= 20)


def test_clamp_mast_collision():
    planner = CollisionPlanner(cfg(), mode="clamp")

    unsafe = tp(0, az=100, el=10)
    sim = type(
        "Sim",
        (),
        {
            "safe_points": [],
            "unsafe_points": [(unsafe, [{"type": "boom_mast_collision_vhf"}])],
        },
    )

    planned = planner.plan(sim)

    assert planned.points[0].el > 10  # elevation bumped upward


def test_clamp_multiple_violations():
    planner = CollisionPlanner(cfg(), mode="clamp")

    unsafe = tp(0, az=400, el=-10)
    violations = [
        {"type": "azimuth_limit"},
        {"type": "elevation_limit"},
        {"type": "ground_clearance_vhf"},
    ]

    sim = type("Sim", (), {"safe_points": [], "unsafe_points": [(unsafe, violations)]})

    planned = planner.plan(sim)
    p = planned.points[0]

    assert p.az == 360
    assert p.el >= 5


def test_violation_objects_supported():
    planner = CollisionPlanner(cfg(), mode="clamp")

    v = Violation(time=tp(0).time, az=100, el=45, type="elevation_limit", details={})

    unsafe = tp(0, az=100, el=-5)

    sim = type("Sim", (), {"safe_points": [], "unsafe_points": [(unsafe, [v])]})

    planned = planner.plan(sim)

    assert planned.points[0].el == 0  # clamped to el_min
