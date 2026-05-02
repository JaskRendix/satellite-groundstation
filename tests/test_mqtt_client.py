import json
from unittest.mock import MagicMock, patch

import pytest

from groundstation.rotator.mqtt_client import RotatorMqttClient
from groundstation.rotator.protocol import TOPIC_COMMAND, TOPIC_HEARTBEAT, TOPIC_STATE


@pytest.fixture
def mock_controller():
    ctrl = MagicMock()
    ctrl.get_state.return_value = {"azimuth": 10, "elevation": 20}
    return ctrl


@pytest.fixture
def mock_mqtt(monkeypatch):
    """Patch paho.mqtt.client.Client with a mock."""
    mock_client = MagicMock()
    monkeypatch.setattr(
        "groundstation.rotator.mqtt_client.mqtt.Client", lambda: mock_client
    )
    return mock_client


@pytest.fixture
def client(mock_controller, mock_mqtt):
    return RotatorMqttClient(
        controller=mock_controller,
        host="localhost",
        port=1883,
        username="user",
        password="pass",
        heartbeat_interval=0.01,
    )


def test_on_connect_success(client, mock_mqtt):
    client._on_connect(mock_mqtt, None, None, rc=0)
    mock_mqtt.subscribe.assert_called_once_with(TOPIC_COMMAND)


def test_on_connect_failure(client, mock_mqtt, caplog):
    caplog.set_level("ERROR")
    client._on_connect(mock_mqtt, None, None, rc=5)
    assert "connection failed" in caplog.text.lower()


def test_handle_move_command(client, mock_controller):
    cmd = {"type": "move", "az": 123, "el": 45}
    client._handle_command(cmd)
    mock_controller.move_to.assert_called_once_with(123, 45)


def test_handle_stop_command(client, mock_controller):
    client._handle_command({"type": "stop"})
    mock_controller.stop.assert_called_once()


def test_handle_home_command(client, mock_controller):
    client._handle_command({"type": "home"})
    mock_controller.home.assert_called_once()


def test_handle_shutdown_command(client, mock_controller, mock_mqtt):
    client._handle_command({"type": "shutdown"})
    mock_controller.shutdown.assert_called_once()
    mock_mqtt.disconnect.assert_called_once()


def test_handle_polarization_command(client, mock_controller):
    client._handle_command({"type": "polarization", "mode": "RHCP"})
    mock_controller.set_polarization.assert_called_once_with("RHCP")


def test_handle_invalid_json(client, caplog):
    caplog.set_level("ERROR")
    msg = MagicMock()
    msg.payload.decode.return_value = "{invalid json"
    client._on_message(None, None, msg)
    assert "invalid mqtt payload" in caplog.text.lower()


def test_heartbeat_loop_publishes(mock_controller, mock_mqtt):
    client = RotatorMqttClient(
        controller=mock_controller,
        host="localhost",
        port=1883,
        username="user",
        password="pass",
        heartbeat_interval=0.001,
    )

    client._running = True
    with patch("time.sleep", side_effect=lambda x: setattr(client, "_running", False)):
        client._heartbeat_loop()

    mock_mqtt.publish.assert_called_with(TOPIC_HEARTBEAT, "alive", qos=0)


def test_state_loop_publishes_state(mock_controller, mock_mqtt):
    client = RotatorMqttClient(
        controller=mock_controller,
        host="localhost",
        port=1883,
        username="user",
        password="pass",
    )

    client._running = True

    with patch("time.sleep", side_effect=lambda x: setattr(client, "_running", False)):
        client._state_loop()

    args, kwargs = mock_mqtt.publish.call_args
    assert args[0] == TOPIC_STATE
    state = json.loads(args[1])
    assert state["azimuth"] == 10
    assert state["elevation"] == 20


def test_start_calls_connect_and_loop_start(client, mock_mqtt):
    client.start()
    mock_mqtt.connect.assert_called_once()
    mock_mqtt.loop_start.assert_called_once()


def test_stop_calls_disconnect_and_loop_stop(client, mock_mqtt):
    client.stop()
    mock_mqtt.loop_stop.assert_called_once()
    mock_mqtt.disconnect.assert_called_once()
