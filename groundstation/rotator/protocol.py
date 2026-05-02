"""
MQTT protocol definitions for the rotator subsystem.

This file defines:
- topic names
- expected JSON schemas for commands
- expected JSON schemas for state messages

Both the station computer and the rotator must follow this protocol.
"""

# Commands sent TO the rotator
TOPIC_COMMAND = "rotator/command"

# Rotator publishes its current state
TOPIC_STATE = "rotator/state"

# Rotator heartbeat ("alive")
TOPIC_HEARTBEAT = "rotator/heartbeat"

# Optional: rotator logs or errors
TOPIC_LOG = "rotator/log"


"""
Command message schema (JSON):

{
    "type": "move" | "stop" | "home" | "shutdown" | "polarization",

    # For type == "move"
    "az": float,        # degrees
    "el": float,        # degrees

    # For type == "polarization"
    "mode": "Vertical" | "Horizontal" | "LHCP" | "RHCP"
}
"""


"""
State message schema (JSON):

{
    "azimuth": float,       # current azimuth in degrees
    "elevation": float,     # current elevation in degrees
    "az_offset": float,     # applied azimuth offset
    "el_offset": float,     # applied elevation offset
    "status": "idle" | "tracking" | "homing" | "error",
    "timestamp": float      # UNIX time
}
"""


VALID_COMMAND_TYPES = {
    "move",
    "stop",
    "home",
    "shutdown",
    "polarization",
}
