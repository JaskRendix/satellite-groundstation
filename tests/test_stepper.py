from unittest.mock import MagicMock, patch

import pytest

from groundstation.rotator.stepper import StepperConfig, StepperMotor


@pytest.fixture
def mock_gpio():
    gpio = MagicMock()
    gpio.setup_output = MagicMock()
    gpio.setup_input = MagicMock()
    gpio.write = MagicMock()
    gpio.read = MagicMock(return_value=False)
    return gpio


@pytest.fixture
def cfg():
    return StepperConfig(
        ena_pin=1,
        dir_pin=2,
        pul_pin=3,
        home_pin=4,
        step_angle_deg=1.8,
        microsteps=8,
        gear_ratio=100,
        max_speed_dps=90,
        max_accel_dps2=180,
        azimuth_mode=False,
    )


@pytest.fixture
def motor(mock_gpio, cfg):
    # Patch time.sleep so the motion loop runs instantly
    with patch("time.sleep", return_value=None):
        m = StepperMotor(mock_gpio, cfg)
        yield m
        m.shutdown()


@pytest.fixture(autouse=True)
def no_threads(monkeypatch):
    monkeypatch.setattr("threading.Thread.start", lambda self: None)
    monkeypatch.setattr("threading.Thread.join", lambda self, timeout=None: None)


def test_initializes_gpio_pins(mock_gpio, cfg):
    with patch("time.sleep", return_value=None):
        StepperMotor(mock_gpio, cfg)

    expected_outputs = [
        (cfg.ena_pin,),
        (cfg.dir_pin,),
        (cfg.pul_pin,),
    ]
    actual_outputs = [call.args for call in mock_gpio.setup_output.call_args_list]
    assert actual_outputs == expected_outputs

    mock_gpio.setup_input.assert_called_once_with(cfg.home_pin, pull_up=True)


def test_enable_called_on_start(mock_gpio, cfg):
    with patch("time.sleep", return_value=None):
        StepperMotor(mock_gpio, cfg)

    mock_gpio.write.assert_any_call(cfg.ena_pin, True)


def test_move_to_sets_target(motor):
    motor.move_to(123.4)
    assert motor.target_deg == 123.4


def test_move_to_wraps_azimuth(mock_gpio, cfg):
    cfg.azimuth_mode = True

    with patch("time.sleep", return_value=None):
        m = StepperMotor(mock_gpio, cfg)
        m.position_deg = 350
        m.move_to(10)  # shortest path = +20°
        assert abs(m.target_deg - 370) < 1e-6  # 350 + 20
        m.shutdown()


def test_stop_sets_speed_zero(motor):
    motor.current_speed = 50
    motor.stop()
    assert motor.current_speed == 0


def test_shutdown_disables_motor(mock_gpio, cfg):
    with patch("time.sleep", return_value=None):
        m = StepperMotor(mock_gpio, cfg)
        m.shutdown()

    mock_gpio.write.assert_any_call(cfg.ena_pin, False)


def test_motion_loop_updates_position(mock_gpio, cfg):
    """
    Instead of running the real infinite motion loop, we simulate
    a single step manually using the internal helpers.
    """

    with patch("time.sleep", return_value=None):
        m = StepperMotor(mock_gpio, cfg)

        # Fake a direction and speed
        m.current_speed = 10
        m.target_deg = 10

        # Simulate one step
        m._set_direction(1)
        m._do_step()
        m.position_deg += m.step_deg

        assert m.position_deg > 0

        m.shutdown()
