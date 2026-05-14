"""
Modern polarization switcher module.

Replaces the legacy PolarizationSwitcher with:
- GPIO abstraction (no direct RPi.GPIO usage)
- clean mode definitions
- validation
- testability (works with MockGpioBackend)
"""

from dataclasses import dataclass

from groundstation.logging import init_logging, metrics

from .gpio import GpioInterface

logger = init_logging("rotator.polarization")

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

        for pin in [
            config.uhf_rel1,
            config.uhf_rel2,
            config.vhf_rel1,
            config.vhf_rel2,
        ]:
            logger.debug(f"Setting up relay pin {pin}")
            self.gpio.setup_output(pin)

        logger.info("Polarization switcher initialized")
        metrics.set("rotator.polarization_changes", 0)

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
        logger.info(f"Setting polarization mode: {mode}")

        if mode not in POLARIZATION_MODES:
            logger.error(f"Invalid polarization mode: {mode}")
            metrics.inc("rotator.polarization_errors")
            raise ValueError(f"Invalid polarization mode: {mode}")

        if mode == "Vertical":
            # all relays off
            self._write(False, False, False, False)

        elif mode == "Horizontal":
            # legacy mapping preserved
            self._write(False, True, False, True)

        elif mode == "LHCP":
            self._write(True, False, True, False)

        elif mode == "RHCP":
            self._write(True, True, True, True)

        metrics.inc("rotator.polarization_changes")
        logger.info(f"Polarization set to {mode}")

    def _write(self, uhf1: bool, uhf2: bool, vhf1: bool, vhf2: bool) -> None:
        logger.debug(f"Relay write: UHF({uhf1}, {uhf2}), VHF({vhf1}, {vhf2})")

        try:
            self.gpio.write(self.cfg.uhf_rel1, uhf1)
            self.gpio.write(self.cfg.uhf_rel2, uhf2)
            self.gpio.write(self.cfg.vhf_rel1, vhf1)
            self.gpio.write(self.cfg.vhf_rel2, vhf2)
        except Exception as e:
            logger.error(f"GPIO relay write error: {e}")
            metrics.inc("rotator.polarization_errors")
            raise
