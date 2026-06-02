from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from groundstation.station.tracking.predictor import TrackPoint

from .constraints import ConstraintChecker, Violation
from .geometry import GeometryModel


@dataclass
class SimulationResult:
    """
    Result of running collision + limit checks over a full track.
    """

    safe_points: list[TrackPoint]
    unsafe_points: list[tuple[TrackPoint, list[Violation]]]


class CollisionSimulator:
    """
    Runs geometric + constraint checks over a sequence of TrackPoint samples.

    Typical usage:

        geom = GeometryModel(collision_cfg)
        checker = ConstraintChecker(constraint_cfg)
        sim = CollisionSimulator(geom, checker)

        result = sim.simulate(track_points)
    """

    def __init__(self, geometry: GeometryModel, checker: ConstraintChecker):
        self.geometry = geometry
        self.checker = checker

    def simulate(self, track: Iterable[TrackPoint]) -> SimulationResult:
        """
        Run simulation over the given track.

        For each TrackPoint:
          - compute Pose via GeometryModel
          - run ConstraintChecker
          - classify as safe / unsafe
        """
        safe: list[TrackPoint] = []
        unsafe: list[tuple[TrackPoint, list[Violation]]] = []

        for tp in track:
            pose = self.geometry.pose(tp.az, tp.el)
            violations = self.checker.check(tp, pose)

            if violations:
                unsafe.append((tp, violations))
            else:
                safe.append(tp)

        return SimulationResult(
            safe_points=safe,
            unsafe_points=unsafe,
        )
