"""Lifecycle primitives for madVR Envy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PowerState(StrEnum):
    """Primary lifecycle state for the device."""

    ON = "on"
    STANDBY = "standby"
    OFF = "off"
    UNKNOWN = "unknown"


class ConnectionState(StrEnum):
    """Current control-plane connection state."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class WakeMode(StrEnum):
    """Supported wake paths."""

    AUTO = "auto"
    IP = "ip"
    WOL = "wol"
    NONE = "none"


@dataclass(slots=True)
class RestoredRuntimeState:
    """Persisted lifecycle/topology state restored on startup."""

    power_state: PowerState = PowerState.UNKNOWN
    mac_address: str | None = None
    profile_groups: dict[str, str] | None = None
    profiles: dict[str, str] | None = None


def normalize_power_state(value: object) -> PowerState:
    """Coerce raw values into a supported power-state enum."""
    if isinstance(value, PowerState):
        return value
    if isinstance(value, str):
        try:
            return PowerState(value)
        except ValueError:
            return PowerState.UNKNOWN
    return PowerState.UNKNOWN


def normalize_connection_state(value: object) -> ConnectionState:
    """Coerce raw values into a supported connection-state enum."""
    if isinstance(value, ConnectionState):
        return value
    if isinstance(value, str):
        try:
            return ConnectionState(value)
        except ValueError:
            return ConnectionState.DISCONNECTED
    return ConnectionState.DISCONNECTED


def normalize_wake_mode(value: object) -> WakeMode:
    """Coerce raw values into a supported wake-mode enum."""
    if isinstance(value, WakeMode):
        return value
    if isinstance(value, str):
        try:
            return WakeMode(value)
        except ValueError:
            return WakeMode.AUTO
    return WakeMode.AUTO


def normalize_mac_address(value: object) -> str | None:
    """Normalize a MAC address to colon-separated lower-case format."""
    if not isinstance(value, str):
        return None

    compact = value.replace(":", "").replace("-", "").strip().lower()
    if len(compact) != 12 or any(char not in "0123456789abcdef" for char in compact):
        return None
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2))
