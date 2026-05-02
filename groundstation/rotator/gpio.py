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
        import RPi.GPIO as GPIO  # imported here so tests don't require it

        self.GPIO = GPIO

        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setwarnings(False)

    def setup_output(self, pin: int) -> None:
        self.GPIO.setup(pin, self.GPIO.OUT)

    def write(self, pin: int, value: bool) -> None:
        self.GPIO.output(pin, self.GPIO.HIGH if value else self.GPIO.LOW)

    def cleanup(self) -> None:
        self.GPIO.cleanup()


class MockGpioBackend(GpioInterface):
    """
    Mock GPIO backend for testing without hardware.

    Stores pin states in a dictionary.
    """

    def __init__(self):
        self.pins: dict[int, bool] = {}

    def setup_output(self, pin: int) -> None:
        self.pins[pin] = False

    def write(self, pin: int, value: bool) -> None:
        self.pins[pin] = value

    def cleanup(self) -> None:
        self.pins.clear()

    def debug_dump(self) -> dict[int, bool]:
        """Return current pin states (for debugging/tests)."""
        return dict(self.pins)
