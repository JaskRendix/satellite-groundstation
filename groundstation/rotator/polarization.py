"""
Modern polarization switcher module.

Replaces the legacy PolarizationSwitcher with:
- GPIO abstraction (no direct RPi.GPIO usage)
- clean mode definitions
- validation
- testability (works with MockGpioBackend)
"""

from dataclasses import dataclass

from .gpio import GpioInterface

POLARIZATION_MODES = {
    "Vertical",
    "Horizontal",
    "LHCP",
    "RHCP",
}


@dataclass
class PolarizationConfig:
    """
    Relay pin assignments for UHF and VHF polarization switching.
    """

    uhf_rel1: int
    uhf_rel2: int
    vhf_rel1: int
    vhf_rel2: int


class PolarizationSwitcher:
    """
    Clean, testable polarization switcher.

    The legacy logic is preserved but rewritten in a modern style.
    """

    def __init__(self, gpio: GpioInterface, config: PolarizationConfig):
        self.gpio = gpio
        self.cfg = config

        # Setup pins
        for pin in [
            config.uhf_rel1,
            config.uhf_rel2,
            config.vhf_rel1,
            config.vhf_rel2,
        ]:
            self.gpio.setup_output(pin)

        # Default mode
        self.set("Vertical")

    def set(self, mode: str) -> None:
        """
        Set antenna polarization mode.

        Supported:
            - Vertical
            - Horizontal
            - LHCP
            - RHCP
        """
        if mode not in POLARIZATION_MODES:
            raise ValueError(f"Invalid polarization mode: {mode}")

        if mode == "Vertical":
            self._write(False, False, False, False)

        elif mode == "Horizontal":
            self._write(False, True, False, True)

        elif mode == "LHCP":
            self._write(True, False, True, False)

        elif mode == "RHCP":
            self._write(True, True, True, True)

    def _write(self, uhf1: bool, uhf2: bool, vhf1: bool, vhf2: bool):
        self.gpio.write(self.cfg.uhf_rel1, uhf1)
        self.gpio.write(self.cfg.uhf_rel2, uhf2)
        self.gpio.write(self.cfg.vhf_rel1, vhf1)
        self.gpio.write(self.cfg.vhf_rel2, vhf2)
