from datetime import datetime, timezone

from groundstation.station.collision.constraints import (
    ConstraintChecker,
    ConstraintConfig,
)
from groundstation.station.collision.geometry import Box3D, Pose
from groundstation.station.tracking.predictor import TrackPoint


def tp(az=100, el=45):
    return TrackPoint(
        time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        az=az,
        el=el,
        range_km=500,
    )


def pose(vhf_box, uhf_box, mast_box):
    return Pose(vhf_box=vhf_box, uhf_box=uhf_box, mast_box=mast_box)


def box(min_x, min_y, min_z, max_x, max_y, max_z):
    return Box3D(min_x, min_y, min_z, max_x, max_y, max_z)


def cfg(**kwargs):
    defaults = dict(
        az_min=0,
        az_max=360,
        el_min=0,
        el_max=180,
        clearance_min_m=0.3,
        forbidden_azimuth_sectors=[],
    )
    defaults.update(kwargs)
    return ConstraintConfig(**defaults)


def test_azimuth_limit_low():
    checker = ConstraintChecker(cfg())
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))
    v = checker.check(tp(az=-10), p)
    assert any(vv.type == "azimuth_limit" for vv in v)


def test_azimuth_limit_high():
    checker = ConstraintChecker(cfg())
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))
    v = checker.check(tp(az=999), p)
    assert any(vv.type == "azimuth_limit" for vv in v)


def test_elevation_limit_low():
    checker = ConstraintChecker(cfg())
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))
    v = checker.check(tp(el=-5), p)
    assert any(vv.type == "elevation_limit" for vv in v)


def test_elevation_limit_high():
    checker = ConstraintChecker(cfg())
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))
    v = checker.check(tp(el=999), p)
    assert any(vv.type == "elevation_limit" for vv in v)


def test_no_limit_violation():
    checker = ConstraintChecker(cfg())
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))
    v = checker.check(tp(az=100, el=45), p)
    assert all(vv.type not in ("azimuth_limit", "elevation_limit") for vv in v)


def test_forbidden_azimuth_inside():
    c = cfg(forbidden_azimuth_sectors=[{"start_deg": 90, "end_deg": 110}])
    checker = ConstraintChecker(c)
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))

    v = checker.check(tp(az=100), p)
    assert any(vv.type == "forbidden_azimuth" for vv in v)


def test_forbidden_azimuth_outside():
    c = cfg(forbidden_azimuth_sectors=[{"start_deg": 90, "end_deg": 110}])
    checker = ConstraintChecker(c)
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))

    v = checker.check(tp(az=50), p)
    assert all(vv.type != "forbidden_azimuth" for vv in v)


def test_forbidden_azimuth_wraparound_inside():
    c = cfg(forbidden_azimuth_sectors=[{"start_deg": 350, "end_deg": 20}])
    checker = ConstraintChecker(c)
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))

    v1 = checker.check(tp(az=355), p)
    v2 = checker.check(tp(az=10), p)

    assert any(vv.type == "forbidden_azimuth" for vv in v1)
    assert any(vv.type == "forbidden_azimuth" for vv in v2)


def test_forbidden_azimuth_wraparound_outside():
    c = cfg(forbidden_azimuth_sectors=[{"start_deg": 350, "end_deg": 20}])
    checker = ConstraintChecker(c)
    p = pose(box(0, 0, 1, 1, 1, 2), box(0, 0, 1, 1, 1, 2), box(-1, -1, 0, 1, 1, 2))

    v = checker.check(tp(az=200), p)
    assert all(vv.type != "forbidden_azimuth" for vv in v)


def test_ground_clearance_vhf_violation():
    checker = ConstraintChecker(cfg(clearance_min_m=0.3))
    vhf = box(0, 0, 0.1, 1, 1, 1)  # min_z < clearance
    uhf = box(0, 0, 1, 1, 1, 2)
    mast = box(-1, -1, 0, 1, 1, 2)

    v = checker.check(tp(), pose(vhf, uhf, mast))
    assert any(vv.type == "ground_clearance_vhf" for vv in v)


def test_ground_clearance_uhf_violation():
    checker = ConstraintChecker(cfg(clearance_min_m=0.3))
    vhf = box(0, 0, 1, 1, 1, 2)
    uhf = box(0, 0, 0.1, 1, 1, 1)  # min_z < clearance
    mast = box(-1, -1, 0, 1, 1, 2)

    v = checker.check(tp(), pose(vhf, uhf, mast))
    assert any(vv.type == "ground_clearance_uhf" for vv in v)


def test_ground_clearance_ok():
    checker = ConstraintChecker(cfg(clearance_min_m=0.3))
    vhf = box(0, 0, 0.5, 1, 1, 1)
    uhf = box(0, 0, 0.6, 1, 1, 1)
    mast = box(-1, -1, 0, 1, 1, 2)

    v = checker.check(tp(), pose(vhf, uhf, mast))
    assert all(
        vv.type not in ("ground_clearance_vhf", "ground_clearance_uhf") for vv in v
    )


def test_boom_mast_collision_vhf():
    checker = ConstraintChecker(cfg())
    vhf = box(-0.1, -0.1, 0, 0.1, 0.1, 1)  # intersects mast
    uhf = box(2, 2, 2, 3, 3, 3)
    mast = box(-0.05, -0.05, 0, 0.05, 0.05, 2)

    v = checker.check(tp(), pose(vhf, uhf, mast))
    assert any(vv.type == "boom_mast_collision_vhf" for vv in v)


def test_boom_mast_collision_uhf():
    checker = ConstraintChecker(cfg())
    vhf = box(2, 2, 2, 3, 3, 3)
    uhf = box(-0.1, -0.1, 0, 0.1, 0.1, 1)  # intersects mast
    mast = box(-0.05, -0.05, 0, 0.05, 0.05, 2)

    v = checker.check(tp(), pose(vhf, uhf, mast))
    assert any(vv.type == "boom_mast_collision_uhf" for vv in v)


def test_no_boom_mast_collision():
    checker = ConstraintChecker(cfg())
    vhf = box(2, 2, 2, 3, 3, 3)
    uhf = box(3, 3, 3, 4, 4, 4)
    mast = box(-0.05, -0.05, 0, 0.05, 0.05, 2)

    v = checker.check(tp(), pose(vhf, uhf, mast))
    assert all("boom_mast_collision" not in vv.type for vv in v)


def test_intersect_true():
    a = box(0, 0, 0, 2, 2, 2)
    b = box(1, 1, 1, 3, 3, 3)
    assert ConstraintChecker._intersect(a, b)


def test_intersect_false():
    a = box(0, 0, 0, 1, 1, 1)
    b = box(2, 2, 2, 3, 3, 3)
    assert not ConstraintChecker._intersect(a, b)
