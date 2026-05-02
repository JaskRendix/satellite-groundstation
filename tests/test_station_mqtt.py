import json
from unittest.mock import MagicMock, patch

import pytest

from groundstation.rotator.protocol import TOPIC_COMMAND, TOPIC_HEARTBEAT, TOPIC_STATE
from groundstation.station.mqtt.client import StationMqttClient


@pytest.fixture(autouse=True)
def no_threads(monkeypatch):
    monkeypatch.setattr("threading.Thread.start", lambda self: None)
    monkeypatch.setattr("threading.Thread.join", lambda self, timeout=None: None)


@pytest.fixture
def fake_mqtt():
    """Mock paho.mqtt.client.Client instance."""
    client = MagicMock()
    client.publish = MagicMock()
    client.connect = MagicMock()
    client.disconnect = MagicMock()
    client.subscribe = MagicMock()
    client.loop = MagicMock()
    return client


@pytest.fixture
def client(fake_mqtt):
    """Create StationMqttClient with mocked paho client."""
    with patch("paho.mqtt.client.Client", return_value=fake_mqtt):
        c = StationMqttClient(
            host="localhost",
            port=1883,
            username="user",
            password="pass",
        )
        return c


def test_start_calls_connect_and_starts_thread(client, fake_mqtt):
    client.start()
    fake_mqtt.connect.assert_called_once_with("localhost", 1883, keepalive=10)


def test_on_connect_success_subscribes(client, fake_mqtt):
    client._on_connect(fake_mqtt, None, None, rc=0)

    fake_mqtt.subscribe.assert_any_call(TOPIC_STATE)
    fake_mqtt.subscribe.assert_any_call(TOPIC_HEARTBEAT)


def test_on_connect_failure_does_not_subscribe(client, fake_mqtt):
    client._on_connect(fake_mqtt, None, None, rc=5)
    fake_mqtt.subscribe.assert_not_called()


def test_on_message_state_callback(client):
    received = {}

    def cb(data):
        received.update(data)

    client.on_state = cb

    msg = MagicMock()
    msg.topic = TOPIC_STATE
    msg.payload = json.dumps({"az": 123}).encode()

    client._on_message(None, None, msg)

    assert received == {"az": 123}


def test_on_message_state_invalid_json(client):
    client.on_state = MagicMock()

    msg = MagicMock()
    msg.topic = TOPIC_STATE
    msg.payload = b"{invalid json"

    client._on_message(None, None, msg)

    client.on_state.assert_not_called()


def test_on_message_heartbeat_callback(client):
    received = []

    def cb(payload):
        received.append(payload)

    client.on_heartbeat = cb

    msg = MagicMock()
    msg.topic = TOPIC_HEARTBEAT
    msg.payload = b"alive"

    client._on_message(None, None, msg)

    assert received == ["alive"]


def test_send_move_publishes(client, fake_mqtt):
    client.send_move(10, 20)

    fake_mqtt.publish.assert_called_once()
    topic, payload = fake_mqtt.publish.call_args[0][:2]

    assert topic == TOPIC_COMMAND
    assert json.loads(payload) == {"type": "move", "az": 10, "el": 20}


def test_send_stop(client, fake_mqtt):
    client.send_stop()
    payload = json.loads(fake_mqtt.publish.call_args[0][1])
    assert payload == {"type": "stop"}


def test_send_home(client, fake_mqtt):
    client.send_home()
    payload = json.loads(fake_mqtt.publish.call_args[0][1])
    assert payload == {"type": "home"}


def test_send_shutdown(client, fake_mqtt):
    client.send_shutdown()
    payload = json.loads(fake_mqtt.publish.call_args[0][1])
    assert payload == {"type": "shutdown"}


def test_send_polarization(client, fake_mqtt):
    client.send_polarization("RHCP")
    payload = json.loads(fake_mqtt.publish.call_args[0][1])
    assert payload == {"type": "polarization", "mode": "RHCP"}


def test_stop_disconnects(client, fake_mqtt):
    client.stop()
    fake_mqtt.disconnect.assert_called_once()
