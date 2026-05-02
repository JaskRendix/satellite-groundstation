import time

from groundstation.rotator.state_machine import RotatorState, RotatorStateMachine


def test_initial_state_is_idle():
    sm = RotatorStateMachine()
    assert sm.get_state() == RotatorState.IDLE
    status = sm.get_status()
    assert status.state == RotatorState.IDLE
    assert status.message == "initialized"
    assert status.timestamp > 0


def test_valid_transition_idle_to_tracking():
    sm = RotatorStateMachine()
    ok = sm.transition(RotatorState.TRACKING, "start tracking")
    assert ok is True
    assert sm.get_state() == RotatorState.TRACKING
    assert sm.get_status().message == "start tracking"


def test_valid_transition_tracking_to_idle():
    sm = RotatorStateMachine()
    sm.transition(RotatorState.TRACKING)
    ok = sm.transition(RotatorState.IDLE, "done")
    assert ok is True
    assert sm.get_state() == RotatorState.IDLE
    assert sm.get_status().message == "done"


def test_invalid_transition_sets_error_state():
    sm = RotatorStateMachine()

    # TRACKING → HOMING is invalid
    sm.transition(RotatorState.TRACKING)
    ok = sm.transition(RotatorState.HOMING)

    assert ok is False
    assert sm.get_state() == RotatorState.ERROR
    assert "Invalid transition" in sm.get_status().message


def test_error_can_transition_back_to_idle():
    sm = RotatorStateMachine()

    sm.transition(RotatorState.TRACKING)
    sm.transition(RotatorState.HOMING)  # invalid → ERROR

    ok = sm.transition(RotatorState.IDLE, "recover")
    assert ok is True
    assert sm.get_state() == RotatorState.IDLE
    assert sm.get_status().message == "recover"


def test_shutdown_is_terminal():
    sm = RotatorStateMachine()

    sm.shutdown()
    assert sm.get_state() == RotatorState.SHUTDOWN

    # No transitions allowed after shutdown
    ok = sm.transition(RotatorState.IDLE)
    assert ok is False
    assert sm.get_state() == RotatorState.ERROR  # forced error


def test_set_error():
    sm = RotatorStateMachine()
    sm.set_error("motor jam")
    assert sm.get_state() == RotatorState.ERROR
    assert sm.get_status().message == "motor jam"


def test_status_as_dict():
    sm = RotatorStateMachine()
    d = sm.get_status().as_dict()

    assert d["state"] == "idle"
    assert "timestamp" in d
    assert isinstance(d["timestamp"], float)


def test_timestamp_updates_on_transition():
    sm = RotatorStateMachine()
    t1 = sm.get_status().timestamp

    time.sleep(0.001)
    sm.transition(RotatorState.TRACKING)

    t2 = sm.get_status().timestamp
    assert t2 > t1
