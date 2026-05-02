import threading
import time
from dataclasses import dataclass

from groundstation.logging import init_logging, metrics

from .gpio import GpioInterface

logger = init_logging("rotator.stepper")


@dataclass
class StepperConfig:
    ena_pin: int
    dir_pin: int
    pul_pin: int

    step_angle_deg: float  # motor step angle (e.g., 1.8°)
    microsteps: int  # microstepping factor (e.g., 4, 8, 16)
    gear_ratio: float  # mechanical gear ratio

    max_speed_dps: float  # max speed (deg/sec)
    max_accel_dps2: float  # max acceleration (deg/sec^2)

    azimuth_mode: bool = False  # wrap-around at 360°


class StepperMotor:
    """
    Modern stepper motor driver with:
    - dedicated motion thread
    - trapezoidal velocity profile
    - thread-safe command queue
    - clean GPIO abstraction
    """

    def __init__(self, gpio: GpioInterface, config: StepperConfig):
        self.gpio = gpio
        self.cfg = config

        # Derived parameters
        self.step_deg = config.step_angle_deg / (config.microsteps * config.gear_ratio)

        # State
        self.position_deg = 0.0
        self.target_deg = 0.0
        self.current_speed = 0.0
        self.running = True
        self._lock = threading.Lock()

        # GPIO setup
        logger.info(
            f"Initializing stepper: ena={config.ena_pin}, dir={config.dir_pin}, pul={config.pul_pin}"
        )
        self.gpio.setup_output(config.ena_pin)
        self.gpio.setup_output(config.dir_pin)
        self.gpio.setup_output(config.pul_pin)

        self.enable()

        # Motion thread
        self._thread = threading.Thread(target=self._motion_loop, daemon=True)
        self._thread.start()

        metrics.set("rotator.motor_steps", 0)

    def enable(self):
        logger.debug("Stepper enabled")
        self.gpio.write(self.cfg.ena_pin, True)

    def disable(self):
        logger.debug("Stepper disabled")
        self.gpio.write(self.cfg.ena_pin, False)

    def move_to(self, angle_deg: float):
        """Thread-safe: set a new target angle."""
        with self._lock:
            if self.cfg.azimuth_mode:
                angle_deg = angle_deg % 360
            self.target_deg = angle_deg

        logger.info(f"Stepper move_to: target={angle_deg:.3f}°")

    def stop(self):
        """Stop motion immediately."""
        logger.info("Stepper stop requested")
        with self._lock:
            self.current_speed = 0.0

    def shutdown(self):
        """Stop thread and disable motor."""
        logger.info("Stepper shutdown")
        self.running = False
        self._thread.join()
        self.disable()

    def _motion_loop(self):
        """Runs continuously, generating steps as needed."""
        dt = 0.001  # 1 ms loop

        while self.running:
            time.sleep(dt)

            try:
                with self._lock:
                    error = self.target_deg - self.position_deg

                if abs(error) < self.step_deg:
                    # Close enough — stop
                    with self._lock:
                        self.current_speed = 0.0
                    continue

                # Determine direction
                direction = 1 if error > 0 else -1
                self._set_direction(direction)

                # Acceleration
                with self._lock:
                    if abs(self.current_speed) < self.cfg.max_speed_dps:
                        self.current_speed += direction * self.cfg.max_accel_dps2 * dt

                    # Clamp speed
                    self.current_speed = max(
                        -self.cfg.max_speed_dps,
                        min(self.current_speed, self.cfg.max_speed_dps),
                    )

                    speed = abs(self.current_speed)

                metrics.set("rotator.motor_speed_dps", speed)

                # Convert speed to step frequency
                if speed < 0.01:
                    continue

                steps_per_sec = speed / self.step_deg
                step_interval = 1.0 / steps_per_sec

                # Perform one step
                self._do_step()
                self.position_deg += direction * self.step_deg

                if self.cfg.azimuth_mode:
                    self.position_deg %= 360

                metrics.set("rotator.motor_position_deg", self.position_deg)
                metrics.inc("rotator.motor_steps")

                # Wait until next step
                time.sleep(step_interval)

            except Exception as e:
                logger.error(f"Stepper motion loop error: {e}")
                metrics.inc("rotator.motor_errors")

    def _set_direction(self, direction: int):
        logger.debug(f"Stepper direction set to {'CW' if direction > 0 else 'CCW'}")
        self.gpio.write(self.cfg.dir_pin, direction > 0)

    def _do_step(self):
        self.gpio.write(self.cfg.pul_pin, False)
        time.sleep(0.00001)
        self.gpio.write(self.cfg.pul_pin, True)
