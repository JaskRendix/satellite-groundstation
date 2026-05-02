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
from groundstation.rotator.state_machine import RotatorStateMachine
from groundstation.rotator.stepper import StepperConfig


# ------------------------------------------------------------
# Load YAML configuration
# ------------------------------------------------------------
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

    az_stepper_cfg = StepperConfig(
        ena_pin=5,
        dir_pin=6,
        pul_pin=13,
        step_angle_deg=1.8,
        microsteps=8,
        gear_ratio=100,
        max_speed_dps=20,
        max_accel_dps2=40,
        azimuth_mode=True,
    )

    el_stepper_cfg = StepperConfig(
        ena_pin=17,
        dir_pin=27,
        pul_pin=22,
        step_angle_deg=1.8,
        microsteps=8,
        gear_ratio=100,
        max_speed_dps=20,
        max_accel_dps2=40,
        azimuth_mode=False,
    )

    az_axis_cfg = AxisConfig(
        stepper=az_stepper_cfg,
        min_deg=0,
        max_deg=360,
        home_deg=0,
    )

    el_axis_cfg = AxisConfig(
        stepper=el_stepper_cfg,
        min_deg=0,
        max_deg=180,
        home_deg=0,
    )

    pol_cfg = PolarizationConfig(
        uhf_rel1=23,
        uhf_rel2=24,
        vhf_rel1=25,
        vhf_rel2=26,
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
    metrics.set("rotator.state", "idle")

    mqtt_cfg = cfg["mqtt"]

    mqtt_client = RotatorMqttClient(
        controller=controller,
        host=mqtt_cfg["host"],
        port=mqtt_cfg["port"],
        username=mqtt_cfg["username"],
        password=mqtt_cfg["password"],
        heartbeat_interval=1.0,
    )

    mqtt_client.start()
    logger.info("MQTT client started")

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
        raise

    finally:
        logger.info("Shutting down rotator...")
        metrics.set("rotator.state", "shutdown")

        mqtt_client.stop()
        controller.shutdown()
        gpio.cleanup()

        logger.info("Rotator daemon stopped")


if __name__ == "__main__":
    main()
