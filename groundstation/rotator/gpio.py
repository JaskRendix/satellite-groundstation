"""
GPIO abstraction layer.

This module defines:
- GpioInterface: abstract base class
- RpiGpioBackend: real Raspberry Pi GPIO implementation
- MockGpioBackend: simulation backend for testing

The rest of the rotator code (stepper, controller, etc.)
must ONLY depend on GpioInterface — never directly on RPi.GPIO.
"""

from abc import ABC, abstractmethod

from groundstation.logging import init_logging, metrics

logger = init_logging("rotator.gpio")


class GpioInterface(ABC):
    """Abstract GPIO interface used by the rotator subsystem."""

    @abstractmethod
    def setup_output(self, pin: int) -> None:
        pass

    @abstractmethod
    def write(self, pin: int, value: bool) -> None:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass


class RpiGpioBackend(GpioInterface):
    """
    Real GPIO backend using RPi.GPIO.
    """

    def __init__(self):
        try:
            import RPi.GPIO as GPIO  # imported here so tests don't require it
        except Exception as e:
            logger.error(f"Failed to import RPi.GPIO: {e}")
            metrics.inc("rotator.gpio_errors")
            raise

        self.GPIO = GPIO

        logger.info("Initializing RPi.GPIO backend")
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setwarnings(False)

    def setup_output(self, pin: int) -> None:
        try:
            logger.debug(f"GPIO setup_output(pin={pin})")
            self.GPIO.setup(pin, self.GPIO.OUT)
        except Exception as e:
            logger.error(f"GPIO setup_output error on pin {pin}: {e}")
            metrics.inc("rotator.gpio_errors")
            raise

    def write(self, pin: int, value: bool) -> None:
        try:
            logger.debug(f"GPIO write(pin={pin}, value={value})")
            self.GPIO.output(pin, self.GPIO.HIGH if value else self.GPIO.LOW)
            metrics.inc("rotator.gpio_writes")
        except Exception as e:
            logger.error(f"GPIO write error on pin {pin}: {e}")
            metrics.inc("rotator.gpio_errors")
            raise

    def cleanup(self) -> None:
        try:
            logger.info("GPIO cleanup")
            self.GPIO.cleanup()
        except Exception as e:
            logger.error(f"GPIO cleanup error: {e}")
            metrics.inc("rotator.gpio_errors")
            raise


class MockGpioBackend(GpioInterface):
    """
    Mock GPIO backend for testing without hardware.

    Stores pin states in a dictionary.
    """

    def __init__(self):
        logger.info("Initializing MockGpioBackend")
        self.pins: dict[int, bool] = {}

    def setup_output(self, pin: int) -> None:
        logger.debug(f"MockGPIO setup_output(pin={pin})")
        self.pins[pin] = False

    def write(self, pin: int, value: bool) -> None:
        logger.debug(f"MockGPIO write(pin={pin}, value={value})")
        self.pins[pin] = value
        metrics.inc("rotator.gpio_writes")

    def cleanup(self) -> None:
        logger.info("MockGPIO cleanup")
        self.pins.clear()

    def debug_dump(self) -> dict[int, bool]:
        """Return current pin states (for debugging/tests)."""
        return dict(self.pins)
