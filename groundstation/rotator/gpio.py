"""
GPIO abstraction layer.

Defines:
- GpioInterface: abstract base class
- RpiGpioBackend: real Raspberry Pi GPIO implementation
- MockGpioBackend: simulation backend for testing

All other rotator code must depend only on GpioInterface.
"""

import time
from abc import ABC, abstractmethod

from groundstation.logging import init_logging, metrics

logger = init_logging("rotator.gpio")


class GpioInterface(ABC):
    """Abstract GPIO interface used by the rotator subsystem."""

    @abstractmethod
    def setup_output(self, pin: int) -> None:
        pass

    @abstractmethod
    def setup_input(self, pin: int, pull_up: bool = True) -> None:
        pass

    @abstractmethod
    def write(self, pin: int, value: bool) -> None:
        pass

    @abstractmethod
    def read(self, pin: int) -> bool:
        """Return True if input is logically 'active'."""
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

    def setup_input(self, pin: int, pull_up: bool = True) -> None:
        try:
            pud = self.GPIO.PUD_UP if pull_up else self.GPIO.PUD_DOWN
            logger.debug(f"GPIO setup_input(pin={pin}, pull_up={pull_up})")
            self.GPIO.setup(pin, self.GPIO.IN, pull_up_down=pud)
        except Exception as e:
            logger.error(f"GPIO setup_input error on pin {pin}: {e}")
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

    def read(self, pin: int) -> bool:
        """
        Read input pin.

        Assumes NC + pull-up wiring: active == LOW.
        Includes a tiny debounce.
        """
        try:
            v1 = self.GPIO.input(pin)
            time.sleep(0.005)
            v2 = self.GPIO.input(pin)
            active = (v1 == self.GPIO.LOW) and (v2 == self.GPIO.LOW)
            logger.debug(f"GPIO read(pin={pin}) -> {active}")
            return active
        except Exception as e:
            logger.error(f"GPIO read error on pin {pin}: {e}")
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

    Stores pin states in dictionaries.
    """

    def __init__(self):
        logger.info("Initializing MockGpioBackend")
        self.outputs: dict[int, bool] = {}
        self.inputs: dict[int, bool] = {}

    def setup_output(self, pin: int) -> None:
        logger.debug(f"MockGPIO setup_output(pin={pin})")
        self.outputs[pin] = False

    def setup_input(self, pin: int, pull_up: bool = True) -> None:
        logger.debug(f"MockGPIO setup_input(pin={pin}, pull_up={pull_up})")
        # default inactive (False) for simplicity
        self.inputs[pin] = False

    def write(self, pin: int, value: bool) -> None:
        logger.debug(f"MockGPIO write(pin={pin}, value={value})")
        self.outputs[pin] = value
        metrics.inc("rotator.gpio_writes")

    def read(self, pin: int) -> bool:
        value = self.inputs.get(pin, False)
        logger.debug(f"MockGPIO read(pin={pin}) -> {value}")
        return value

    def cleanup(self) -> None:
        logger.info("MockGPIO cleanup")
        self.outputs.clear()
        self.inputs.clear()

    def debug_dump(self) -> dict[int, bool]:
        """Return current output pin states (for debugging/tests)."""
        return dict(self.outputs)
