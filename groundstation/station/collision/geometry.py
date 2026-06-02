from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from typing import Protocol


@dataclass
class Vec3:
    x: float
    y: float
    z: float


@dataclass
class Box3D:
    """
    Axis-aligned bounding box in station coordinates (meters).
    """

    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float


@dataclass
class Pose:
    """
    Geometric pose of the rotator + antennas at a given az/el.
    """

    vhf_box: Box3D
    uhf_box: Box3D
    mast_box: Box3D


class CollisionConfig(Protocol):
    """
    Minimal config interface we need from the app-level config.
    This can be backed by your existing config loader.
    """

    mast_height_m: float
    boom_vhf_length_m: float
    boom_uhf_length_m: float
    boom_offset_m: float


@dataclass
class DefaultCollisionConfig:
    """
    Reasonable defaults if collision section is missing in config.
    """

    mast_height_m: float = 2.0
    boom_vhf_length_m: float = 1.5
    boom_uhf_length_m: float = 1.2
    boom_offset_m: float = 0.15


class GeometryModel:
    """
    Simple geometric model of the mast + VHF/UHF booms.

    Coordinate system (station frame):
      - origin: rotator az/el pivot
      - +X: azimuth 0° (north, for example)
      - +Y: azimuth 90°
      - +Z: up

    We approximate each boom as a thin box extending from the pivot
    along its direction vector, starting at boom_offset_m above the pivot.
    """

    def __init__(self, cfg: CollisionConfig | None = None):
        self.cfg = cfg or DefaultCollisionConfig()

    def pose(self, az_deg: float, el_deg: float) -> Pose:
        """
        Compute the 3D pose (bounding boxes) for a given az/el.
        """
        az_rad = radians(az_deg)
        el_rad = radians(el_deg)

        # Direction vector of the main boom axis
        dir_vec = self._direction_vector(az_rad, el_rad)

        vhf_box = self._boom_box(
            length=self.cfg.boom_vhf_length_m,
            dir_vec=dir_vec,
        )
        uhf_box = self._boom_box(
            length=self.cfg.boom_uhf_length_m,
            dir_vec=dir_vec,
        )
        mast_box = self._mast_box()

        return Pose(
            vhf_box=vhf_box,
            uhf_box=uhf_box,
            mast_box=mast_box,
        )

    @staticmethod
    def _direction_vector(az_rad: float, el_rad: float) -> Vec3:
        """
        Convert az/el (radians) to a unit direction vector in station frame.
        """
        ce = cos(el_rad)
        x = cos(az_rad) * ce
        y = sin(az_rad) * ce
        z = sin(el_rad)
        return Vec3(x, y, z)

    def _boom_box(self, length: float, dir_vec: Vec3) -> Box3D:
        """
        Approximate a boom as a thin box from pivot+offset to pivot+offset+length*dir.
        We add a small thickness to make collision checks easier.
        """
        # Start point: pivot + vertical offset
        start = Vec3(0.0, 0.0, self.cfg.boom_offset_m)
        end = Vec3(
            start.x + dir_vec.x * length,
            start.y + dir_vec.y * length,
            start.z + dir_vec.z * length,
        )

        # Small thickness (radius) around the boom axis
        r = 0.05  # 5 cm

        min_x = min(start.x, end.x) - r
        max_x = max(start.x, end.x) + r
        min_y = min(start.y, end.y) - r
        max_y = max(start.y, end.y) + r
        min_z = min(start.z, end.z) - r
        max_z = max(start.z, end.z) + r

        return Box3D(min_x, min_y, min_z, max_x, max_y, max_z)

    def _mast_box(self) -> Box3D:
        """
        Approximate mast as a vertical cylinder → axis-aligned box.
        """
        radius = 0.05  # 5 cm mast radius
        h = self.cfg.mast_height_m

        return Box3D(
            min_x=-radius,
            max_x=radius,
            min_y=-radius,
            max_y=radius,
            min_z=0.0,
            max_z=h,
        )
