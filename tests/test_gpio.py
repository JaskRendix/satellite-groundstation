from unittest.mock import MagicMock, patch

import pytest

from groundstation.rotator.gpio import GpioInterface, MockGpioBackend, RpiGpioBackend


def test_gpio_interface_is_abstract():
    class BadImpl(GpioInterface):
        pass

    with pytest.raises(TypeError):
        BadImpl()  # missing abstract methods


def test_mock_gpio_setup_output():
    gpio = MockGpioBackend()
    gpio.setup_output(5)
    assert gpio.pins[5] is False


def test_mock_gpio_write():
    gpio = MockGpioBackend()
    gpio.setup_output(7)
    gpio.write(7, True)
    assert gpio.pins[7] is True


def test_mock_gpio_cleanup():
    gpio = MockGpioBackend()
    gpio.setup_output(1)
    gpio.write(1, True)
    gpio.cleanup()
    assert gpio.pins == {}


def test_mock_gpio_debug_dump():
    gpio = MockGpioBackend()
    gpio.setup_output(3)
    gpio.write(3, True)
    dump = gpio.debug_dump()
    assert dump == {3: True}
    assert dump is not gpio.pins  # must be a copy


def test_rpi_gpio_backend_initializes_gpio():
    fake_gpio = MagicMock()
    fake_gpio.BCM = 123
    fake_gpio.OUT = 456
    fake_gpio.HIGH = True
    fake_gpio.LOW = False

    fake_rpi = MagicMock()
    fake_rpi.GPIO = fake_gpio

    with patch.dict("sys.modules", {"RPi": fake_rpi, "RPi.GPIO": fake_gpio}):
        backend = RpiGpioBackend()

    fake_gpio.setmode.assert_called_once_with(fake_gpio.BCM)
    fake_gpio.setwarnings.assert_called_once_with(False)


def test_rpi_gpio_setup_output():
    fake_gpio = MagicMock()
    fake_gpio.OUT = 99

    fake_rpi = MagicMock()
    fake_rpi.GPIO = fake_gpio

    with patch.dict("sys.modules", {"RPi": fake_rpi, "RPi.GPIO": fake_gpio}):
        backend = RpiGpioBackend()
        backend.setup_output(10)

    fake_gpio.setup.assert_called_once_with(10, fake_gpio.OUT)


def test_rpi_gpio_write():
    fake_gpio = MagicMock()
    fake_gpio.HIGH = True
    fake_gpio.LOW = False

    fake_rpi = MagicMock()
    fake_rpi.GPIO = fake_gpio

    with patch.dict("sys.modules", {"RPi": fake_rpi, "RPi.GPIO": fake_gpio}):
        backend = RpiGpioBackend()
        backend.write(8, True)
        backend.write(8, False)

    fake_gpio.output.assert_any_call(8, True)
    fake_gpio.output.assert_any_call(8, False)


def test_rpi_gpio_cleanup():
    fake_gpio = MagicMock()

    fake_rpi = MagicMock()
    fake_rpi.GPIO = fake_gpio

    with patch.dict("sys.modules", {"RPi": fake_rpi, "RPi.GPIO": fake_gpio}):
        backend = RpiGpioBackend()
        backend.cleanup()

    fake_gpio.cleanup.assert_called_once()
