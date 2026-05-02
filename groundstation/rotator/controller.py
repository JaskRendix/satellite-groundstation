from dataclasses import dataclass

from groundstation.logging import init_logging, metrics

from .gpio import GpioInterface
from .polarization import PolarizationSwitcher
from .stepper import StepperConfig, StepperMotor

logger = init_logging("rotator.controller")


@dataclass
class AxisConfig:
    stepper: StepperConfig
    min_deg: float
    max_deg: float
    home_deg: float = 0.0


class RotatorController:
    """
    High-level rotator controller.

    Responsibilities:
    - manage azimuth and elevation axes
    - apply offsets
    - expose move_to / home / stop API
    - integrate polarization control
    - provide current state snapshot
    """

    def __init__(
        self,
        gpio: GpioInterface,
        az_config: AxisConfig,
        el_config: AxisConfig,
        polarization: PolarizationSwitcher | None = None,
    ):
        self.gpio = gpio
        self.az_axis = StepperMotor(gpio, az_config.stepper)
        self.el_axis = StepperMotor(gpio, el_config.stepper)

        self.az_offset = 0.0
        self.el_offset = 0.0

        self.az_limits = (az_config.min_deg, az_config.max_deg)
        self.el_limits = (el_config.min_deg, el_config.max_deg)

        self.az_home = az_config.home_deg
        self.el_home = el_config.home_deg

        self.polarization = polarization

        logger.info(
            f"RotatorController initialized "
            f"(az_limits={self.az_limits}, el_limits={self.el_limits})"
        )

    def set_offsets(self, az_offset: float, el_offset: float) -> None:
        logger.info(f"Setting offsets: az={az_offset}, el={el_offset}")
        self.az_offset = az_offset
        self.el_offset = el_offset

    def move_to(self, az_deg: float, el_deg: float) -> None:
        """
        Move to commanded az/el, applying offsets and enforcing limits.
        """
        logger.debug(f"move_to requested az={az_deg}, el={el_deg}")

        az_cmd = az_deg + self.az_offset
        el_cmd = el_deg + self.el_offset

        # Clamp + detect violations
        if not (self.az_limits[0] <= az_cmd <= self.az_limits[1]):
            logger.warning(f"Azimuth limit violation: {az_cmd}")
            metrics.inc("rotator.limit_violations")
        if not (self.el_limits[0] <= el_cmd <= self.el_limits[1]):
            logger.warning(f"Elevation limit violation: {el_cmd}")
            metrics.inc("rotator.limit_violations")

        az_cmd = self._clamp(az_cmd, *self.az_limits)
        el_cmd = self._clamp(el_cmd, *self.el_limits)

        self.az_axis.move_to(az_cmd)
        self.el_axis.move_to(el_cmd)

        metrics.set("rotator.azimuth_deg", az_cmd)
        metrics.set("rotator.elevation_deg", el_cmd)

        logger.info(f"Rotator moved to az={az_cmd}, el={el_cmd}")

    def home(self) -> None:
        logger.info("Homing rotator")
        self.az_axis.move_to(self.az_home)
        self.el_axis.move_to(self.el_home)

        metrics.set("rotator.azimuth_deg", self.az_home)
        metrics.set("rotator.elevation_deg", self.el_home)

    def stop(self) -> None:
        logger.info("Stopping rotator")
        self.az_axis.stop()
        self.el_axis.stop()

    def shutdown(self) -> None:
        logger.info("Shutting down rotator controller")
        self.az_axis.shutdown()
        self.el_axis.shutdown()

    def set_polarization(self, mode: str) -> None:
        logger.info(f"Setting polarization: {mode}")
        if self.polarization is not None:
            self.polarization.set(mode)

    def get_state(self) -> dict:
        """
        Return a snapshot of current rotator state.
        """
        state = {
            "azimuth": self.az_axis.position_deg,
            "elevation": self.el_axis.position_deg,
            "az_offset": self.az_offset,
            "el_offset": self.el_offset,
        }
        logger.debug(f"State snapshot: {state}")
        return state

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(value, hi))
