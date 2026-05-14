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
    home_pin: int
    step_angle_deg: float
    microsteps: int
    gear_ratio: float
    max_speed_dps: float
    max_accel_dps2: float
    azimuth_mode: bool = False


class StepperMotor:
    """
    Stepper motor driver with:
    - dedicated motion thread
    - trapezoidal-like velocity profile
    - shortest-path azimuth mode
    - homing via limit switch
    """

    def __init__(self, gpio: GpioInterface, config: StepperConfig):
        self.gpio = gpio
        self.cfg = config

        self.step_deg = config.step_angle_deg / (config.microsteps * config.gear_ratio)

        self.position_deg = 0.0
        self.target_deg = 0.0
        self.current_speed = 0.0
        self.running = True
        self.is_homed = False
        self._paused = False
        self._lock = threading.Lock()

        logger.info(
            f"Initializing stepper: ena={config.ena_pin}, "
            f"dir={config.dir_pin}, pul={config.pul_pin}, home={config.home_pin}"
        )

        self.gpio.setup_output(config.ena_pin)
        self.gpio.setup_output(config.dir_pin)
        self.gpio.setup_output(config.pul_pin)
        self.gpio.setup_input(config.home_pin, pull_up=True)

        self.enable()

        self._thread = threading.Thread(target=self._motion_loop, daemon=True)
        self._thread.start()

        metrics.set("rotator.motor_steps", 0)

    def enable(self) -> None:
        logger.debug("Stepper enabled")
        self.gpio.write(self.cfg.ena_pin, True)

    def disable(self) -> None:
        logger.debug("Stepper disabled")
        self.gpio.write(self.cfg.ena_pin, False)

    def pause(self) -> None:
        logger.info("Stepper paused")
        with self._lock:
            self._paused = True
            self.current_speed = 0.0

    def resume(self) -> None:
        logger.info("Stepper resumed")
        with self._lock:
            self._paused = False

    def move_to(self, angle_deg: float) -> None:
        """Thread-safe: set a new target angle."""
        with self._lock:
            if self.cfg.azimuth_mode:
                # shortest-path delta in [-180, 180)
                diff = (angle_deg - self.position_deg + 180.0) % 360.0 - 180.0
                self.target_deg = self.position_deg + diff
            else:
                self.target_deg = angle_deg

        logger.info(f"Stepper move_to: target={self.target_deg:.3f}°")

    def stop(self) -> None:
        """Stop motion immediately (soft stop)."""
        logger.info("Stepper stop requested")
        with self._lock:
            self.current_speed = 0.0

    def shutdown(self) -> None:
        """Stop thread and disable motor."""
        logger.info("Stepper shutdown")
        self.running = False
        self._thread.join()
        self.disable()

    def find_home(self) -> None:
        """
        Physical homing routine using the home switch.

        Assumes NC + pull-up wiring: active when pressed.
        """
        logger.info("Starting homing routine")
        self.pause()

        # Move slowly in negative direction until switch is active
        try:
            self._set_direction(-1)
            while not self.gpio.read(self.cfg.home_pin):
                self._do_step()
                time.sleep(0.005)

            # Reset position at home
            with self._lock:
                self.position_deg = 0.0
                self.target_deg = 0.0
                self.is_homed = True

            metrics.set("rotator.motor_position_deg", self.position_deg)
            logger.info("Homing complete, position set to 0.0°")
        except Exception as e:
            logger.error(f"Homing error: {e}")
            metrics.inc("rotator.motor_errors")
            raise
        finally:
            self.resume()

    def _motion_loop(self) -> None:
        """Runs continuously, generating steps as needed."""
        dt = 0.001  # 1 ms loop

        while self.running:
            time.sleep(dt)

            try:
                with self._lock:
                    if self._paused:
                        continue

                    error = self.target_deg - self.position_deg

                if abs(error) < self.step_deg:
                    with self._lock:
                        self.current_speed = 0.0
                    continue

                direction = 1 if error > 0 else -1
                self._set_direction(direction)

                with self._lock:
                    # accelerate toward max speed
                    if abs(self.current_speed) < self.cfg.max_speed_dps:
                        self.current_speed += direction * self.cfg.max_accel_dps2 * dt

                    # clamp speed
                    self.current_speed = max(
                        -self.cfg.max_speed_dps,
                        min(self.current_speed, self.cfg.max_speed_dps),
                    )
                    speed = abs(self.current_speed)

                metrics.set("rotator.motor_speed_dps", speed)

                if speed < 0.01:
                    continue

                steps_per_sec = speed / self.step_deg
                step_interval = 1.0 / steps_per_sec

                self._do_step()
                self.position_deg += direction * self.step_deg

                if self.cfg.azimuth_mode:
                    self.position_deg %= 360.0

                metrics.set("rotator.motor_position_deg", self.position_deg)
                metrics.inc("rotator.motor_steps")

                time.sleep(step_interval)

            except Exception as e:
                logger.error(f"Stepper motion loop error: {e}")
                metrics.inc("rotator.motor_errors")

    def _set_direction(self, direction: int) -> None:
        logger.debug(f"Stepper direction set to {'CW' if direction > 0 else 'CCW'}")
        self.gpio.write(self.cfg.dir_pin, direction > 0)

    def _do_step(self) -> None:
        self.gpio.write(self.cfg.pul_pin, False)
        time.sleep(0.00001)
        self.gpio.write(self.cfg.pul_pin, True)
