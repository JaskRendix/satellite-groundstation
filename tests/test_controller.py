from unittest.mock import MagicMock

import pytest

from groundstation.rotator.controller import AxisConfig, RotatorController
from groundstation.rotator.stepper import StepperConfig


@pytest.fixture
def mock_gpio():
    return MagicMock()


@pytest.fixture
def mock_stepper(monkeypatch):
    """
    Replace StepperMotor with a mock that tracks calls and exposes position_deg.
    """

    class MockStepper:
        def __init__(self, gpio, config):
            self.position_deg = 0
            self.move_to = MagicMock(side_effect=self._move_to)
            self.stop = MagicMock()
            self.shutdown = MagicMock()

        def _move_to(self, deg):
            self.position_deg = deg

    monkeypatch.setattr("groundstation.rotator.controller.StepperMotor", MockStepper)
    return MockStepper


@pytest.fixture
def minimal_stepper_cfg():
    """A valid StepperConfig with minimal realistic values."""
    return StepperConfig(
        ena_pin=1,
        dir_pin=2,
        pul_pin=3,
        step_angle_deg=1.8,
        microsteps=8,
        gear_ratio=100,
        max_speed_dps=20,
        max_accel_dps2=40,
    )


@pytest.fixture
def controller(mock_gpio, mock_stepper, minimal_stepper_cfg):
    az_cfg = AxisConfig(
        stepper=minimal_stepper_cfg,
        min_deg=0,
        max_deg=360,
        home_deg=0,
    )
    el_cfg = AxisConfig(
        stepper=minimal_stepper_cfg,
        min_deg=0,
        max_deg=180,
        home_deg=0,
    )

    return RotatorController(
        gpio=mock_gpio,
        az_config=az_cfg,
        el_config=el_cfg,
        polarization=None,
    )


def test_set_offsets(controller):
    controller.set_offsets(10, -5)
    assert controller.az_offset == 10
    assert controller.el_offset == -5


def test_move_to_applies_offsets_and_clamps(controller):
    controller.set_offsets(10, -5)

    controller.move_to(az_deg=350, el_deg=190)

    assert controller.az_axis.position_deg == 360
    assert controller.el_axis.position_deg == 180


def test_move_to_without_offsets(controller):
    controller.move_to(100, 45)
    assert controller.az_axis.position_deg == 100
    assert controller.el_axis.position_deg == 45


def test_home_moves_to_home_positions(controller):
    controller.home()
    assert controller.az_axis.position_deg == controller.az_home
    assert controller.el_axis.position_deg == controller.el_home


def test_stop_calls_stepper_stop(controller):
    controller.stop()
    controller.az_axis.stop.assert_called_once()
    controller.el_axis.stop.assert_called_once()


def test_shutdown_calls_stepper_shutdown(controller):
    controller.shutdown()
    controller.az_axis.shutdown.assert_called_once()
    controller.el_axis.shutdown.assert_called_once()


def test_set_polarization_calls_switcher(mock_gpio, mock_stepper, minimal_stepper_cfg):
    mock_polarization = MagicMock()
    mock_polarization.set = MagicMock()

    az_cfg = AxisConfig(
        stepper=minimal_stepper_cfg,
        min_deg=0,
        max_deg=360,
        home_deg=0,
    )
    el_cfg = AxisConfig(
        stepper=minimal_stepper_cfg,
        min_deg=0,
        max_deg=180,
        home_deg=0,
    )

    controller = RotatorController(
        gpio=mock_gpio,
        az_config=az_cfg,
        el_config=el_cfg,
        polarization=mock_polarization,
    )

    controller.set_polarization("RHCP")
    mock_polarization.set.assert_called_once_with("RHCP")


def test_get_state_returns_snapshot(controller):
    controller.set_offsets(10, -5)
    controller.move_to(100, 50)

    state = controller.get_state()

    assert state["azimuth"] == controller.az_axis.position_deg
    assert state["elevation"] == controller.el_axis.position_deg
    assert state["az_offset"] == 10
    assert state["el_offset"] == -5
