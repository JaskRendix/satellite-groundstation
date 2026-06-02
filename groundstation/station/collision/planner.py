from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from groundstation.station.tracking.predictor import TrackPoint

from .constraints import ConstraintConfig
from .simulator import SimulationResult


@dataclass
class PlannedTrack:
    """
    Final track after applying collision-avoidance policy.
    """

    points: list[TrackPoint]
    dropped_segments: list[tuple[datetime, datetime]]
    warnings: list[str]


class CollisionPlanner:
    """
    Applies a policy ("strict" or "clamp") to a SimulationResult.

    strict:
        - drop all unsafe points
        - produce only safe segments

    clamp:
        - clamp az/el to nearest safe values
        - keep full timeline
        - unsafe points become safe by modification
    """

    def __init__(self, cfg: ConstraintConfig, mode: str = "strict"):
        self.cfg = cfg
        self.mode = mode.lower()

        if self.mode not in ("strict", "clamp"):
            raise ValueError(f"Unknown planner mode: {mode}")

    @staticmethod
    def _vtype(v: Any) -> str:
        if isinstance(v, dict):
            return v.get("type", "")
        return getattr(v, "type", "")

    @staticmethod
    def _vdetails(v: Any) -> dict:
        if isinstance(v, dict):
            return v.get("details", {})
        return getattr(v, "details", {})

    def plan(self, sim: SimulationResult) -> PlannedTrack:
        if self.mode == "strict":
            return self._plan_strict(sim)
        return self._plan_clamp(sim)

    def _plan_strict(self, sim: SimulationResult) -> PlannedTrack:
        safe = sim.safe_points
        dropped = []
        warnings = []

        if sim.unsafe_points:
            warnings.append("Unsafe segments dropped due to collision risk.")

            current_start = None
            last_time = None

            for tp, _ in sim.unsafe_points:
                if current_start is None:
                    current_start = tp.time
                last_time = tp.time

            if current_start and last_time:
                dropped.append((current_start, last_time))

        return PlannedTrack(points=safe, dropped_segments=dropped, warnings=warnings)

    def _plan_clamp(self, sim: SimulationResult) -> PlannedTrack:
        warnings = []
        points: list[TrackPoint] = []

        unsafe_map = {tp.time: violations for tp, violations in sim.unsafe_points}

        # Merge safe + unsafe
        all_points = sim.safe_points + [tp for tp, _ in sim.unsafe_points]

        for tp in all_points:
            if tp.time not in unsafe_map:
                points.append(tp)
                continue

            violations = unsafe_map[tp.time]
            clamped = self._clamp_point(tp, violations)
            points.append(clamped)

        if sim.unsafe_points:
            warnings.append("Unsafe points clamped to nearest safe values.")

        points.sort(key=lambda p: p.time)

        return PlannedTrack(points=points, dropped_segments=[], warnings=warnings)

    def _clamp_point(self, tp: TrackPoint, violations: list[Any]) -> TrackPoint:
        az = tp.az
        el = tp.el

        for v in violations:
            vtype = self._vtype(v)
            details = self._vdetails(v)

            if vtype == "azimuth_limit":
                az = min(max(az, self.cfg.az_min), self.cfg.az_max)

            elif vtype == "elevation_limit":
                el = min(max(el, self.cfg.el_min), self.cfg.el_max)

            elif vtype.startswith("ground_clearance"):
                el = max(el, self._min_el_for_clearance())

            elif vtype == "forbidden_azimuth":
                az = self._clamp_azimuth_outside_sector(az, details)

            elif vtype.startswith("boom_mast_collision"):
                el = min(max(el + 2.0, self.cfg.el_min), self.cfg.el_max)

        return TrackPoint(tp.time, az, el, tp.range_km)

    def _min_el_for_clearance(self) -> float:
        return max(self.cfg.el_min, 5.0)

    def _clamp_azimuth_outside_sector(self, az: float, sector: dict) -> float:
        start = sector.get("start_deg", 0) % 360
        end = sector.get("end_deg", 0) % 360
        az = az % 360

        if start <= end:
            if start <= az <= end:
                return start - 1.0 if (az - start) < (end - az) else end + 1.0
        else:
            if az >= start or az <= end:
                return start - 1.0 if az >= start else end + 1.0

        return az
