from dataclasses import dataclass

from .gpio import GpioInterface
from .polarization import PolarizationSwitcher
from .stepper import StepperConfig, StepperMotor


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

    def set_offsets(self, az_offset: float, el_offset: float) -> None:
        self.az_offset = az_offset
        self.el_offset = el_offset

    def move_to(self, az_deg: float, el_deg: float) -> None:
        """
        Move to commanded az/el, applying offsets and enforcing limits.
        """
        az_cmd = az_deg + self.az_offset
        el_cmd = el_deg + self.el_offset

        az_cmd = self._clamp(az_cmd, *self.az_limits)
        el_cmd = self._clamp(el_cmd, *self.el_limits)

        self.az_axis.move_to(az_cmd)
        self.el_axis.move_to(el_cmd)

    def home(self) -> None:
        """
        Move both axes to their home positions.
        (Assumes home positions are known; limit switches can be integrated later.)
        """
        self.az_axis.move_to(self.az_home)
        self.el_axis.move_to(self.el_home)

    def stop(self) -> None:
        self.az_axis.stop()
        self.el_axis.stop()

    def shutdown(self) -> None:
        self.az_axis.shutdown()
        self.el_axis.shutdown()

    def set_polarization(self, mode: str) -> None:
        if self.polarization is not None:
            self.polarization.set(mode)

    def get_state(self) -> dict:
        """
        Return a snapshot of current rotator state.
        """
        return {
            "azimuth": self.az_axis.position_deg,
            "elevation": self.el_axis.position_deg,
            "az_offset": self.az_offset,
            "el_offset": self.el_offset,
        }

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(value, hi))
