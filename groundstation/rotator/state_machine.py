import time
from dataclasses import dataclass
from enum import Enum, auto


class RotatorState(Enum):
    IDLE = auto()
    TRACKING = auto()
    HOMING = auto()
    ERROR = auto()
    SHUTDOWN = auto()


@dataclass
class RotatorStatus:
    state: RotatorState
    message: str = ""
    timestamp: float = 0.0

    def as_dict(self):
        return {
            "state": self.state.name.lower(),
            "message": self.message,
            "timestamp": self.timestamp,
        }


class RotatorStateMachine:
    """
    Centralized state machine for the rotator.

    Responsibilities:
    - track current state
    - validate transitions
    - expose a clean API for controller + MQTT client
    """

    VALID_TRANSITIONS = {
        RotatorState.IDLE: {
            RotatorState.TRACKING,
            RotatorState.HOMING,
            RotatorState.SHUTDOWN,
        },
        RotatorState.TRACKING: {
            RotatorState.IDLE,
            RotatorState.ERROR,
            RotatorState.SHUTDOWN,
        },
        RotatorState.HOMING: {
            RotatorState.IDLE,
            RotatorState.ERROR,
            RotatorState.SHUTDOWN,
        },
        RotatorState.ERROR: {RotatorState.IDLE, RotatorState.SHUTDOWN},
        RotatorState.SHUTDOWN: set(),  # terminal
    }

    def __init__(self):
        self._status = RotatorStatus(
            state=RotatorState.IDLE,
            message="initialized",
            timestamp=time.time(),
        )

    def get_state(self) -> RotatorState:
        return self._status.state

    def get_status(self) -> RotatorStatus:
        return self._status

    def transition(self, new_state: RotatorState, message: str = "") -> bool:
        """
        Attempt a state transition.
        Returns True if successful, False if invalid.
        """

        current = self._status.state
        allowed = self.VALID_TRANSITIONS[current]

        if new_state not in allowed:
            # Invalid transition
            self._set_status(
                RotatorState.ERROR,
                f"Invalid transition {current.name} → {new_state.name}",
            )
            return False

        self._set_status(new_state, message)
        return True

    def set_error(self, message: str):
        self._set_status(RotatorState.ERROR, message)

    def shutdown(self):
        self._set_status(RotatorState.SHUTDOWN, "shutdown requested")

    def _set_status(self, state: RotatorState, message: str):
        self._status = RotatorStatus(
            state=state,
            message=message,
            timestamp=time.time(),
        )
