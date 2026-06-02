from __future__ import annotations

from dataclasses import dataclass

from groundstation.station.tracking.predictor import PassEvent, Predictor, TrackPoint
from groundstation.station.tracking.tle_manager import TleManager

from .constraints import ConstraintChecker, ConstraintConfig
from .geometry import DefaultCollisionConfig, GeometryModel
from .planner import CollisionPlanner, PlannedTrack
from .simulator import CollisionSimulator, SimulationResult


@dataclass
class CollisionPipelineConfig:
    """
    High-level config wrapper for the entire collision pipeline.
    """

    enabled: bool
    mode: str
    mast_height_m: float
    boom_vhf_length_m: float
    boom_uhf_length_m: float
    boom_offset_m: float
    clearance_min_m: float
    forbidden_azimuth_sectors: list


class TrackingPipeline:
    """
    Full collision-aware tracking pipeline.

    Responsibilities:
      - load TLE
      - generate track (Predictor)
      - compute geometry (GeometryModel)
      - check constraints (ConstraintChecker)
      - simulate (CollisionSimulator)
      - plan safe track (CollisionPlanner)

    This is the single entry point used by the Scheduler callback.
    """

    def __init__(
        self,
        predictor: Predictor,
        tle_manager: TleManager,
        rotator_cfg: dict,
        collision_cfg: dict,
    ):
        self.predictor = predictor
        self.tle_manager = tle_manager

        self.collision_enabled = collision_cfg.get("enabled", True)

        self.pipeline_cfg = CollisionPipelineConfig(
            enabled=collision_cfg.get("enabled", True),
            mode=collision_cfg.get("mode", "strict"),
            mast_height_m=collision_cfg.get("mast_height_m", 2.0),
            boom_vhf_length_m=collision_cfg.get("boom_vhf_length_m", 1.5),
            boom_uhf_length_m=collision_cfg.get("boom_uhf_length_m", 1.2),
            boom_offset_m=collision_cfg.get("boom_offset_m", 0.15),
            clearance_min_m=collision_cfg.get("clearance_min_m", 0.3),
            forbidden_azimuth_sectors=collision_cfg.get(
                "forbidden_azimuth_sectors", []
            ),
        )

        self.geometry = GeometryModel(
            DefaultCollisionConfig(
                mast_height_m=self.pipeline_cfg.mast_height_m,
                boom_vhf_length_m=self.pipeline_cfg.boom_vhf_length_m,
                boom_uhf_length_m=self.pipeline_cfg.boom_uhf_length_m,
                boom_offset_m=self.pipeline_cfg.boom_offset_m,
            )
        )

        self.checker = ConstraintChecker(
            ConstraintConfig(
                az_min=rotator_cfg["azimuth"]["min_deg"],
                az_max=rotator_cfg["azimuth"]["max_deg"],
                el_min=rotator_cfg["elevation"]["min_deg"],
                el_max=rotator_cfg["elevation"]["max_deg"],
                clearance_min_m=self.pipeline_cfg.clearance_min_m,
                forbidden_azimuth_sectors=self.pipeline_cfg.forbidden_azimuth_sectors,
            )
        )

        self.simulator = CollisionSimulator(self.geometry, self.checker)
        self.planner = CollisionPlanner(
            cfg=self.checker.cfg,
            mode=self.pipeline_cfg.mode,
        )

    def compute_safe_track(
        self, norad_id: int
    ) -> tuple[list[TrackPoint], PassEvent | None, PlannedTrack]:
        """
        Full pipeline:
          - load TLE
          - generate track
          - simulate collisions
          - plan safe track

        Returns:
          (raw_track, pass_event, planned_track)
        """
        tle_text = self.tle_manager.get_tle_text(norad_id)
        if not tle_text:
            return [], None, PlannedTrack([], [], ["No TLE available"])

        # Generate raw track
        track, event = self.predictor.generate_track(tle_text)
        if not track:
            return [], None, PlannedTrack([], [], ["No valid pass"])

        # If disabled → return raw track unchanged
        if not self.collision_enabled:
            return track, event, PlannedTrack(track, [], [])

        # Run simulation
        sim_result: SimulationResult = self.simulator.simulate(track)

        # Plan safe track
        planned: PlannedTrack = self.planner.plan(sim_result)

        return track, event, planned
