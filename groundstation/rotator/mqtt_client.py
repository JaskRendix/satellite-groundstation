import json
import threading
import time

import paho.mqtt.client as mqtt

from .controller import RotatorController
from .protocol import TOPIC_COMMAND, TOPIC_HEARTBEAT, TOPIC_STATE


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

    def start(self):
        """Start MQTT connection and background threads."""
        self.client.connect(self.host, self.port, keepalive=10)
        self.client.loop_start()

        self._heartbeat_thread.start()
        self._state_thread.start()

    def stop(self):
        """Stop MQTT and background threads."""
        self._running = False
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Rotator MQTT connected")
            client.subscribe(TOPIC_COMMAND)
        else:
            print(f"Rotator MQTT connection failed: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print("Invalid MQTT payload")
            return

        self._handle_command(payload)

    def _handle_command(self, cmd: dict):
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

        if cmd_type == "move":
            az = cmd.get("az")
            el = cmd.get("el")
            if az is not None and el is not None:
                self.controller.move_to(az, el)

        elif cmd_type == "stop":
            self.controller.stop()

        elif cmd_type == "home":
            self.controller.home()

        elif cmd_type == "shutdown":
            self.controller.shutdown()
            self.stop()

        elif cmd_type == "polarization":
            mode = cmd.get("mode")
            if mode:
                self.controller.set_polarization(mode)

    def _heartbeat_loop(self):
        """Publish heartbeat every second."""
        while self._running:
            self.client.publish(TOPIC_HEARTBEAT, "alive", qos=0)
            time.sleep(self.heartbeat_interval)

    def _state_loop(self):
        """Publish rotator state periodically."""
        while self._running:
            state = self.controller.get_state()
            self.client.publish(TOPIC_STATE, json.dumps(state), qos=0)
            time.sleep(0.5)
