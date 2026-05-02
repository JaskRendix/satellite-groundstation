import json
from unittest.mock import MagicMock, patch

import pytest

from groundstation.rotator.protocol import TOPIC_COMMAND, TOPIC_HEARTBEAT, TOPIC_STATE
from groundstation.station.mqtt.client import StationMqttClient


@pytest.fixture
def mock_mqtt(monkeypatch):
    """Patch paho.mqtt.client.Client with a mock."""
    mock_client = MagicMock()
    monkeypatch.setattr(
        "groundstation.station.mqtt.client.mqtt.Client", lambda: mock_client
    )
    return mock_client


@pytest.fixture
def client(mock_mqtt):
    return StationMqttClient(
        host="localhost",
        port=1883,
        username="user",
        password="pass",
    )


def test_on_connect_success(client, mock_mqtt, capsys):
    client._on_connect(mock_mqtt, None, None, rc=0)
    captured = capsys.readouterr()
    assert "connected" in captured.out.lower()
    mock_mqtt.subscribe.assert_any_call(TOPIC_STATE)
    mock_mqtt.subscribe.assert_any_call(TOPIC_HEARTBEAT)


def test_on_connect_failure(client, mock_mqtt, capsys):
    client._on_connect(mock_mqtt, None, None, rc=5)
    captured = capsys.readouterr()
    assert "failed" in captured.out.lower()


def test_handle_invalid_json(client):
    msg = MagicMock()
    msg.topic = TOPIC_STATE
    msg.payload.decode.return_value = "{invalid json"

    # Should not raise, should not call callback
    cb = MagicMock()
    client.on_state = cb

    client._on_message(None, None, msg)
    cb.assert_not_called()


def test_handle_state_message(client):
    msg = MagicMock()
    msg.topic = TOPIC_STATE
    msg.payload.decode.return_value = json.dumps({"azimuth": 10, "elevation": 20})

    cb = MagicMock()
    client.on_state = cb

    client._on_message(None, None, msg)
    cb.assert_called_once_with({"azimuth": 10, "elevation": 20})


def test_handle_heartbeat_message(client):
    msg = MagicMock()
    msg.topic = TOPIC_HEARTBEAT
    msg.payload.decode.return_value = "alive"

    cb = MagicMock()
    client.on_heartbeat = cb

    client._on_message(None, None, msg)
    cb.assert_called_once_with("alive")


def test_publish_move(client, mock_mqtt):
    client.send_move(123, 45)
    args, kwargs = mock_mqtt.publish.call_args
    assert args[0] == TOPIC_COMMAND
    payload = json.loads(args[1])
    assert payload == {"type": "move", "az": 123, "el": 45}


def test_publish_stop(client, mock_mqtt):
    client.send_stop()
    args, kwargs = mock_mqtt.publish.call_args
    payload = json.loads(args[1])
    assert payload == {"type": "stop"}


def test_publish_home(client, mock_mqtt):
    client.send_home()
    args, kwargs = mock_mqtt.publish.call_args
    payload = json.loads(args[1])
    assert payload == {"type": "home"}


def test_publish_shutdown(client, mock_mqtt):
    client.send_shutdown()
    args, kwargs = mock_mqtt.publish.call_args
    payload = json.loads(args[1])
    assert payload == {"type": "shutdown"}


def test_publish_polarization(client, mock_mqtt):
    client.send_polarization("RHCP")
    args, kwargs = mock_mqtt.publish.call_args
    payload = json.loads(args[1])
    assert payload == {"type": "polarization", "mode": "RHCP"}


def test_start_calls_connect_and_starts_thread(client, mock_mqtt):
    with patch.object(client._thread, "start") as start_mock:
        client.start()
        mock_mqtt.connect.assert_called_once()
        start_mock.assert_called_once()


def test_stop_calls_disconnect(client, mock_mqtt):
    client.stop()
    mock_mqtt.disconnect.assert_called_once()
