from unittest.mock import MagicMock

import pytest

from groundstation.logging import metrics
from groundstation.rotator.controller import AxisConfig, RotatorController
from groundstation.rotator.polarization import PolarizationConfig, PolarizationSwitcher
from groundstation.rotator.stepper import StepperConfig


@pytest.fixture
def mock_gpio():
    gpio = MagicMock()
    return gpio


@pytest.fixture
def stepper_cfg():
    return StepperConfig(
        ena_pin=1,
        dir_pin=2,
        pul_pin=3,
        step_angle_deg=1.8,
        microsteps=8,
        gear_ratio=100,
        max_speed_dps=20,
        max_accel_dps2=40,
        azimuth_mode=False,
    )


@pytest.fixture
def axis_cfg(stepper_cfg):
    return AxisConfig(
        stepper=stepper_cfg,
        min_deg=0,
        max_deg=180,
        home_deg=0,
    )


@pytest.fixture
def mock_polarization(mock_gpio):
    cfg = PolarizationConfig(1, 2, 3, 4)
    pol = PolarizationSwitcher(mock_gpio, cfg)
    pol.set = MagicMock()
    return pol


@pytest.fixture
def controller(mock_gpio, axis_cfg, mock_polarization):
    metrics.reset()  # reset metrics
    return RotatorController(
        gpio=mock_gpio,
        az_config=axis_cfg,
        el_config=axis_cfg,
        polarization=mock_polarization,
    )


def test_move_to_logs_and_updates_metrics(controller, caplog):
    caplog.set_level("INFO")

    controller.move_to(10, 20)

    assert "moved to az=10" in caplog.text.lower()
    assert metrics.get("rotator.azimuth_deg") == 10
    assert metrics.get("rotator.elevation_deg") == 20


def test_move_to_clamps_and_logs_limit_violation(controller, caplog):
    caplog.set_level("WARNING")

    controller.move_to(999, -999)

    assert "limit violation" in caplog.text.lower()
    assert metrics.get("rotator.limit_violations") == 2  # az + el


def test_home_logs_and_updates_metrics(controller, caplog):
    caplog.set_level("INFO")

    controller.home()

    assert "homing" in caplog.text.lower()
    assert metrics.get("rotator.azimuth_deg") == 0
    assert metrics.get("rotator.elevation_deg") == 0


def test_stop_logs(controller, caplog):
    caplog.set_level("INFO")

    controller.stop()

    assert "stopping rotator" in caplog.text.lower()


def test_shutdown_logs(controller, caplog):
    caplog.set_level("INFO")

    controller.shutdown()

    assert "shutting down rotator controller" in caplog.text.lower()


def test_set_polarization_logs_and_calls_switcher(
    controller, mock_polarization, caplog
):
    caplog.set_level("INFO")

    controller.set_polarization("RHCP")

    assert "setting polarization" in caplog.text.lower()
    mock_polarization.set.assert_called_once_with("RHCP")


def test_get_state_returns_snapshot(controller):
    state = controller.get_state()
    assert "azimuth" in state
    assert "elevation" in state
    assert "az_offset" in state
    assert "el_offset" in state
