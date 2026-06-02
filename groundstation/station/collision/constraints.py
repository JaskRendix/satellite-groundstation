from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from groundstation.station.tracking.predictor import TrackPoint

from .geometry import Box3D, Pose


@dataclass
class Violation:
    """
    A single collision or limit violation at a specific time.
    """

    time: datetime
    az: float
    el: float
    type: str
    details: dict


@dataclass
class ConstraintConfig:
    """
    Configuration for collision + limit checking.
    """

    # Mechanical limits
    az_min: float
    az_max: float
    el_min: float
    el_max: float

    # Ground clearance
    clearance_min_m: float = 0.3

    # Forbidden azimuth sectors
    # List of dicts: { "start_deg": X, "end_deg": Y }
    forbidden_azimuth_sectors: list = None

    def __post_init__(self):
        if self.forbidden_azimuth_sectors is None:
            self.forbidden_azimuth_sectors = []


class ConstraintChecker:
    """
    Evaluates whether a given TrackPoint + Pose violates:
      - mechanical limits
      - ground clearance
      - forbidden azimuth sectors
      - boom–mast collision
      - boom–ground collision
    """

    def __init__(self, cfg: ConstraintConfig):
        self.cfg = cfg

    def check(self, tp: TrackPoint, pose: Pose) -> list[Violation]:
        """
        Return a list of violations for this track point.
        """
        violations = []

        # Mechanical limits
        violations.extend(self._check_limits(tp))

        # Forbidden azimuth sectors
        violations.extend(self._check_forbidden_azimuth(tp))

        # Ground clearance
        violations.extend(self._check_ground_clearance(tp, pose))

        # Boom–mast collision
        violations.extend(self._check_boom_mast_collision(tp, pose))

        return violations

    def _check_limits(self, tp: TrackPoint) -> list[Violation]:
        v = []

        if tp.az < self.cfg.az_min or tp.az > self.cfg.az_max:
            v.append(
                Violation(
                    time=tp.time,
                    az=tp.az,
                    el=tp.el,
                    type="azimuth_limit",
                    details={
                        "min": self.cfg.az_min,
                        "max": self.cfg.az_max,
                    },
                )
            )

        if tp.el < self.cfg.el_min or tp.el > self.cfg.el_max:
            v.append(
                Violation(
                    time=tp.time,
                    az=tp.az,
                    el=tp.el,
                    type="elevation_limit",
                    details={
                        "min": self.cfg.el_min,
                        "max": self.cfg.el_max,
                    },
                )
            )

        return v

    def _check_forbidden_azimuth(self, tp: TrackPoint) -> list[Violation]:
        v = []
        az = tp.az % 360

        for sector in self.cfg.forbidden_azimuth_sectors:
            start = sector["start_deg"] % 360
            end = sector["end_deg"] % 360

            if start <= end:
                inside = start <= az <= end
            else:
                # Sector wraps around 360
                inside = az >= start or az <= end

            if inside:
                v.append(
                    Violation(
                        time=tp.time,
                        az=tp.az,
                        el=tp.el,
                        type="forbidden_azimuth",
                        details=sector,
                    )
                )

        return v

    def _check_ground_clearance(self, tp: TrackPoint, pose: Pose) -> list[Violation]:
        v = []

        # Check VHF boom
        if pose.vhf_box.min_z < self.cfg.clearance_min_m:
            v.append(
                Violation(
                    time=tp.time,
                    az=tp.az,
                    el=tp.el,
                    type="ground_clearance_vhf",
                    details={
                        "min_z": pose.vhf_box.min_z,
                        "required": self.cfg.clearance_min_m,
                    },
                )
            )

        # Check UHF boom
        if pose.uhf_box.min_z < self.cfg.clearance_min_m:
            v.append(
                Violation(
                    time=tp.time,
                    az=tp.az,
                    el=tp.el,
                    type="ground_clearance_uhf",
                    details={
                        "min_z": pose.uhf_box.min_z,
                        "required": self.cfg.clearance_min_m,
                    },
                )
            )

        return v

    def _check_boom_mast_collision(self, tp: TrackPoint, pose: Pose) -> list[Violation]:
        v = []

        if self._intersect(pose.vhf_box, pose.mast_box):
            v.append(
                Violation(
                    time=tp.time,
                    az=tp.az,
                    el=tp.el,
                    type="boom_mast_collision_vhf",
                    details={},
                )
            )

        if self._intersect(pose.uhf_box, pose.mast_box):
            v.append(
                Violation(
                    time=tp.time,
                    az=tp.az,
                    el=tp.el,
                    type="boom_mast_collision_uhf",
                    details={},
                )
            )

        return v

    @staticmethod
    def _intersect(a: Box3D, b: Box3D) -> bool:
        """
        Axis-aligned bounding box intersection test.
        """
        return not (
            a.max_x < b.min_x
            or a.min_x > b.max_x
            or a.max_y < b.min_y
            or a.min_y > b.max_y
            or a.max_z < b.min_z
            or a.min_z > b.max_z
        )
