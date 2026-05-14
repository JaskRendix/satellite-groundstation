import json
import threading
import time

import paho.mqtt.client as mqtt

from groundstation.logging import init_logging, metrics

from .controller import RotatorController
from .protocol import TOPIC_COMMAND, TOPIC_HEARTBEAT, TOPIC_STATE

logger = init_logging("rotator.mqtt")


class RotatorMqttClient:
    """
    Rotator-side MQTT client.

    Responsibilities:
    - connect to broker
    - receive commands (move, stop, home, shutdown, polarization)
    - publish rotator state periodically
    - publish heartbeat
    """

    def __init__(
        self,
        controller: RotatorController,
        host: str,
        port: int,
        username: str,
        password: str,
        heartbeat_interval: float = 1.0,
    ):
        self.controller = controller
        self.heartbeat_interval = heartbeat_interval

        self.client = mqtt.Client()
        if username:
            self.client.username_pw_set(username, password=password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        self.host = host
        self.port = port

        self._running = True

        # Background threads
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._state_thread = threading.Thread(target=self._state_loop, daemon=True)

        logger.info(f"MQTT client initialized for {host}:{port}")

    def start(self) -> None:
        """Start MQTT connection and background threads."""
        logger.info("Starting MQTT client")
        self.client.connect(self.host, self.port, keepalive=10)
        self.client.loop_start()

        self._heartbeat_thread.start()
        self._state_thread.start()

    def stop(self) -> None:
        """Stop MQTT and background threads."""
        logger.info("Stopping MQTT client")
        self._running = False
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            logger.error(f"Error stopping MQTT client: {e}")
            metrics.inc("rotator.mqtt_errors")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Rotator MQTT connected successfully")
            client.subscribe(TOPIC_COMMAND)
        else:
            logger.error(f"Rotator MQTT connection failed: rc={rc}")
            metrics.inc("rotator.mqtt_errors")

    def _on_message(self, client, userdata, msg):
        start = time.time()

        logger.debug(f"MQTT message received on {msg.topic}")

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Invalid MQTT payload (JSON decode error)")
            metrics.inc("rotator.mqtt_errors")
            return

        metrics.inc("rotator.commands_received")
        self._handle_command(payload)

        latency = (time.time() - start) * 1000.0
        metrics.observe("rotator.mqtt_latency_ms", latency)

    def _handle_command(self, cmd: dict) -> None:
        """
        Expected command schema (protocol.py):

        {
            "type": "move" | "stop" | "home" | "shutdown" | "polarization",
            "az": float,
            "el": float,
            "mode": "Vertical" | "Horizontal" | "LHCP" | "RHCP"
        }
        """

        cmd_type = cmd.get("type")
        logger.info(f"Handling command: {cmd_type}")

        if cmd_type == "move":
            az = cmd.get("az")
            el = cmd.get("el")
            if az is not None and el is not None:
                self.controller.move_to(float(az), float(el))
            else:
                logger.error("Move command missing az/el")
                metrics.inc("rotator.mqtt_errors")

        elif cmd_type == "stop":
            self.controller.stop()

        elif cmd_type == "home":
            self.controller.home()

        elif cmd_type == "shutdown":
            logger.warning("Shutdown command received")
            self.controller.shutdown()
            self.stop()

        elif cmd_type == "polarization":
            mode = cmd.get("mode")
            if mode:
                self.controller.set_polarization(str(mode))
            else:
                logger.error("Polarization command missing mode")
                metrics.inc("rotator.mqtt_errors")

        else:
            logger.error(f"Unknown command type: {cmd_type}")
            metrics.inc("rotator.mqtt_errors")

    def _heartbeat_loop(self) -> None:
        """Publish heartbeat periodically."""
        while self._running:
            try:
                self.client.publish(TOPIC_HEARTBEAT, "alive", qos=0)
                metrics.inc("rotator.heartbeat_sent")
            except Exception as e:
                logger.error(f"Error publishing heartbeat: {e}")
                metrics.inc("rotator.mqtt_errors")
            time.sleep(self.heartbeat_interval)

    def _state_loop(self) -> None:
        """Publish rotator state periodically."""
        while self._running:
            try:
                state = self.controller.get_state()
                self.client.publish(TOPIC_STATE, json.dumps(state), qos=0)
                metrics.inc("rotator.state_published")
            except Exception as e:
                logger.error(f"Error publishing state: {e}")
                metrics.inc("rotator.mqtt_errors")
            time.sleep(0.5)
