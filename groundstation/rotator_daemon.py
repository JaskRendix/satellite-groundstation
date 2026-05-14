#!/usr/bin/env python3
"""
Rotator Daemon

Initializes:
- GPIO backend
- Stepper motors
- Rotator controller
- Polarization switcher
- State machine
- MQTT client
- Logging + metrics

Runs indefinitely as a systemd service.
"""

import time
from pathlib import Path

import yaml

from groundstation.logging import init_logging, metrics
from groundstation.rotator.controller import AxisConfig, RotatorController
from groundstation.rotator.gpio import RpiGpioBackend
from groundstation.rotator.mqtt_client import RotatorMqttClient
from groundstation.rotator.polarization import PolarizationConfig, PolarizationSwitcher
from groundstation.rotator.state_machine import RotatorState, RotatorStateMachine
from groundstation.rotator.stepper import StepperConfig


def load_config():
    config_path = Path("/home/pi/groundstation/config/default.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()

    log_cfg = cfg.get("logging", {})
    logger = init_logging(
        name="rotator.daemon",
        level=log_cfg.get("level", "INFO"),
        fmt=log_cfg.get("format", "text"),
        logfile=log_cfg.get("file"),
    )

    logger.info("Rotator daemon starting")
    metrics.set("rotator.state", "initializing")

    gpio = RpiGpioBackend()
    logger.info("GPIO backend initialized")

    rot_cfg = cfg["rotator"]
    az_cfg = rot_cfg["azimuth"]
    el_cfg = rot_cfg["elevation"]
    pol_cfg_raw = rot_cfg["polarization"]

    az_stepper_cfg = StepperConfig(
        ena_pin=az_cfg["ena_pin"],
        dir_pin=az_cfg["dir_pin"],
        pul_pin=az_cfg["pul_pin"],
        home_pin=az_cfg["home_pin"],
        step_angle_deg=az_cfg["step_angle_deg"],
        microsteps=az_cfg["microsteps"],
        gear_ratio=az_cfg["gear_ratio"],
        max_speed_dps=az_cfg["max_speed_dps"],
        max_accel_dps2=az_cfg["max_accel_dps2"],
        azimuth_mode=bool(az_cfg.get("azimuth_mode", True)),
    )

    el_stepper_cfg = StepperConfig(
        ena_pin=el_cfg["ena_pin"],
        dir_pin=el_cfg["dir_pin"],
        pul_pin=el_cfg["pul_pin"],
        home_pin=el_cfg["home_pin"],
        step_angle_deg=el_cfg["step_angle_deg"],
        microsteps=el_cfg["microsteps"],
        gear_ratio=el_cfg["gear_ratio"],
        max_speed_dps=el_cfg["max_speed_dps"],
        max_accel_dps2=el_cfg["max_accel_dps2"],
        azimuth_mode=bool(el_cfg.get("azimuth_mode", False)),
    )

    az_axis_cfg = AxisConfig(
        stepper=az_stepper_cfg,
        min_deg=az_cfg["min_deg"],
        max_deg=az_cfg["max_deg"],
        home_deg=az_cfg["home_deg"],
    )

    el_axis_cfg = AxisConfig(
        stepper=el_stepper_cfg,
        min_deg=el_cfg["min_deg"],
        max_deg=el_cfg["max_deg"],
        home_deg=el_cfg["home_deg"],
    )

    pol_cfg = PolarizationConfig(
        uhf_rel1=pol_cfg_raw["uhf_rel1"],
        uhf_rel2=pol_cfg_raw["uhf_rel2"],
        vhf_rel1=pol_cfg_raw["vhf_rel1"],
        vhf_rel2=pol_cfg_raw["vhf_rel2"],
    )
    polarization = PolarizationSwitcher(gpio, pol_cfg)
    logger.info("Polarization switcher initialized")

    controller = RotatorController(
        gpio=gpio,
        az_config=az_axis_cfg,
        el_config=el_axis_cfg,
        polarization=polarization,
    )
    logger.info("Rotator controller initialized")

    state_machine = RotatorStateMachine()
    state_machine.set_state(RotatorState.IDLE)
    metrics.set("rotator.state", "idle")

    logger.info("Performing homing sequence")
    try:
        controller.home()
        state_machine.set_state(RotatorState.IDLE)
        logger.info("Homing complete")
    except Exception as e:
        logger.error(f"Homing failed: {e}")
        state_machine.set_state(RotatorState.ERROR)

    mqtt_cfg = cfg["mqtt"]

    mqtt_client = RotatorMqttClient(
        controller=controller,
        host=mqtt_cfg["host"],
        port=mqtt_cfg["port"],
        username=mqtt_cfg.get("username"),
        password=mqtt_cfg.get("password"),
        heartbeat_interval=1.0,
    )

    mqtt_client.start()
    logger.info("MQTT client started")

    state_machine.set_state(RotatorState.TRACKING)
    metrics.set("rotator.state", "running")
    logger.info("Rotator daemon fully initialized")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.warning("Rotator daemon interrupted by user")

    except Exception as e:
        logger.error(f"Fatal rotator daemon error: {e}")
        metrics.set("rotator.state", "error")
        state_machine.set_state(RotatorState.ERROR)
        raise

    finally:
        logger.info("Shutting down rotator...")
        metrics.set("rotator.state", "shutdown")
        state_machine.set_state(RotatorState.SHUTDOWN)

        mqtt_client.stop()
        controller.shutdown()
        gpio.cleanup()

        logger.info("Rotator daemon stopped")


if __name__ == "__main__":
    main()
