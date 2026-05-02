"""
Station-side MQTT client.

Responsibilities:
- send commands to rotator (move, stop, home, shutdown, polarization)
- receive rotator state updates
- receive heartbeat
- expose async callbacks for GUI or tracking logic
"""

import json
import threading
from collections.abc import Callable

import paho.mqtt.client as mqtt

from groundstation.rotator.protocol import TOPIC_COMMAND, TOPIC_HEARTBEAT, TOPIC_STATE


class StationMqttClient:
    """
    Async-friendly MQTT client for the station computer.

    Uses paho-mqtt in a background thread while exposing async callbacks.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        on_state: Callable[[dict], None] | None = None,
        on_heartbeat: Callable[[str], None] | None = None,
    ):
        self.host = host
        self.port = port

        self.on_state = on_state
        self.on_heartbeat = on_heartbeat

        # MQTT client
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password=password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        # Background thread for MQTT loop
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._running = False

    def start(self):
        """Start MQTT connection and background thread."""
        self._running = True
        self.client.connect(self.host, self.port, keepalive=10)
        self._thread.start()

    def stop(self):
        """Stop MQTT client."""
        self._running = False
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Station MQTT connected")
            client.subscribe(TOPIC_STATE)
            client.subscribe(TOPIC_HEARTBEAT)
        else:
            print(f"Station MQTT connection failed: {rc}")

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8")

        if msg.topic == TOPIC_STATE:
            try:
                data = json.loads(payload)
                if self.on_state:
                    self.on_state(data)
            except json.JSONDecodeError:
                pass

        elif msg.topic == TOPIC_HEARTBEAT:
            if self.on_heartbeat:
                self.on_heartbeat(payload)

    def _loop(self):
        """Run paho-mqtt loop in a background thread."""
        while self._running:
            self.client.loop(timeout=1.0)

    def send_move(self, az: float, el: float):
        cmd = {"type": "move", "az": az, "el": el}
        self._publish(cmd)

    def send_stop(self):
        self._publish({"type": "stop"})

    def send_home(self):
        self._publish({"type": "home"})

    def send_shutdown(self):
        self._publish({"type": "shutdown"})

    def send_polarization(self, mode: str):
        self._publish({"type": "polarization", "mode": mode})

    def _publish(self, payload: dict):
        self.client.publish(TOPIC_COMMAND, json.dumps(payload), qos=0)
