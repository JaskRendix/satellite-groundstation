#!/usr/bin/env python3
"""
Rotator Shutdown Script

This script is executed when systemd stops the rotator service.
It ensures:
- motors are disabled
- GPIO is cleaned up
- no threads are left running
"""

from pathlib import Path

import yaml

from groundstation.rotator.controller import AxisConfig, RotatorController
from groundstation.rotator.gpio import RpiGpioBackend
from groundstation.rotator.polarization import PolarizationConfig, PolarizationSwitcher
from groundstation.rotator.stepper import StepperConfig


def load_config():
    config_path = Path("/home/pi/groundstation/config/default.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()

    # GPIO backend
    gpio = RpiGpioBackend()

    # Minimal stepper configs (same as daemon)
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

    az_axis_cfg = AxisConfig(az_stepper_cfg, 0, 360, 0)
    el_axis_cfg = AxisConfig(el_stepper_cfg, 0, 180, 0)

    # Polarization config
    pol_cfg = PolarizationConfig(
        uhf_rel1=23,
        uhf_rel2=24,
        vhf_rel1=25,
        vhf_rel2=26,
    )
    polarization = PolarizationSwitcher(gpio, pol_cfg)

    # Controller
    controller = RotatorController(
        gpio=gpio,
        az_config=az_axis_cfg,
        el_config=el_axis_cfg,
        polarization=polarization,
    )

    print("Stopping rotator motors...")
    controller.stop()

    print("Disabling motors...")
    controller.shutdown()

    print("Cleaning up GPIO...")
    gpio.cleanup()

    print("Rotator shutdown complete")


if __name__ == "__main__":
    main()
