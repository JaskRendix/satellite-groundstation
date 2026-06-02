from math import radians, sqrt

import pytest

from groundstation.station.collision.geometry import (
    Box3D,
    DefaultCollisionConfig,
    GeometryModel,
    Vec3,
)


@pytest.fixture
def cfg():
    return DefaultCollisionConfig(
        mast_height_m=2.0,
        boom_vhf_length_m=1.5,
        boom_uhf_length_m=1.2,
        boom_offset_m=0.15,
    )


@pytest.fixture
def geom(cfg):
    return GeometryModel(cfg)


def test_direction_vector_az0_el0(geom):
    v = geom._direction_vector(0, 0)
    assert pytest.approx(v.x) == 1.0
    assert pytest.approx(v.y) == 0.0
    assert pytest.approx(v.z) == 0.0


def test_direction_vector_az90_el0(geom):
    v = geom._direction_vector(radians(90), 0)
    assert pytest.approx(v.x, abs=1e-6) == 0.0
    assert pytest.approx(v.y, abs=1e-6) == 1.0
    assert pytest.approx(v.z) == 0.0


def test_direction_vector_el90(geom):
    v = geom._direction_vector(0, 1.57079632679)  # az=0, el=90°
    assert pytest.approx(v.x, abs=1e-6) == 0.0
    assert pytest.approx(v.y, abs=1e-6) == 0.0
    assert pytest.approx(v.z, abs=1e-6) == 1.0


def test_boom_box_length_and_offset(geom, cfg):
    dir_vec = Vec3(1, 0, 0)  # boom pointing +X
    box = geom._boom_box(cfg.boom_vhf_length_m, dir_vec)

    # Start point is (0,0,offset)
    start_z = cfg.boom_offset_m

    assert pytest.approx(box.min_z) == start_z - 0.05
    assert pytest.approx(box.max_z) == start_z + 0.05

    # Boom extends along +X
    assert pytest.approx(box.max_x) == cfg.boom_vhf_length_m + 0.05
    assert pytest.approx(box.min_x) == -0.05


def test_boom_box_direction_changes(geom):
    # Boom pointing +Y
    dir_vec = Vec3(0, 1, 0)
    box = geom._boom_box(1.0, dir_vec)

    assert pytest.approx(box.max_y) == 1.0 + 0.05
    assert pytest.approx(box.min_y) == -0.05


def test_boom_box_vertical(geom):
    # Boom pointing straight up
    dir_vec = Vec3(0, 0, 1)
    box = geom._boom_box(1.0, dir_vec)

    # X/Y should be just thickness
    assert pytest.approx(box.min_x) == -0.05
    assert pytest.approx(box.max_x) == 0.05
    assert pytest.approx(box.min_y) == -0.05
    assert pytest.approx(box.max_y) == 0.05

    # Z should extend from offset upward
    assert pytest.approx(box.max_z) == 1.0 + geom.cfg.boom_offset_m + 0.05


def test_mast_box_dimensions(geom, cfg):
    mast = geom._mast_box()

    assert mast.min_x == -0.05
    assert mast.max_x == 0.05
    assert mast.min_y == -0.05
    assert mast.max_y == 0.05
    assert mast.min_z == 0.0
    assert mast.max_z == cfg.mast_height_m


def test_pose_contains_three_boxes(geom):
    pose = geom.pose(az_deg=0, el_deg=0)

    assert pose.vhf_box is not None
    assert pose.uhf_box is not None
    assert pose.mast_box is not None


def test_pose_vhf_and_uhf_different_lengths(geom, cfg):
    pose = geom.pose(az_deg=0, el_deg=0)

    assert (
        pose.vhf_box.max_x - pose.vhf_box.min_x
        > pose.uhf_box.max_x - pose.uhf_box.min_x
    )
    assert cfg.boom_vhf_length_m > cfg.boom_uhf_length_m


def test_pose_changes_with_azimuth(geom):
    pose1 = geom.pose(az_deg=0, el_deg=0)
    pose2 = geom.pose(az_deg=90, el_deg=0)

    assert pose1.vhf_box.max_x != pose2.vhf_box.max_x
    assert pose1.vhf_box.max_y != pose2.vhf_box.max_y


def test_pose_changes_with_elevation(geom):
    pose1 = geom.pose(az_deg=0, el_deg=0)
    pose2 = geom.pose(az_deg=0, el_deg=45)

    assert pose1.vhf_box.max_z != pose2.vhf_box.max_z


@pytest.mark.parametrize("az", [0, 90, 180, 270])
@pytest.mark.parametrize("el", [0, 45, 90])
def test_pose_edge_cases(geom, az, el):
    pose = geom.pose(az_deg=az, el_deg=el)
    assert isinstance(pose.vhf_box, Box3D)
    assert isinstance(pose.uhf_box, Box3D)
    assert isinstance(pose.mast_box, Box3D)


def test_direction_vector_unit_length(geom):
    v = geom._direction_vector(1.0, 0.5)
    length = sqrt(v.x**2 + v.y**2 + v.z**2)
    assert pytest.approx(length, abs=1e-6) == 1.0
