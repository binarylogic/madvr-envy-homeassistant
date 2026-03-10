"""Lifecycle helpers for madVR Envy entities."""

from __future__ import annotations

from enum import StrEnum


class PowerState(StrEnum):
    """Primary power/lifecycle states exposed to Home Assistant."""

    ON = "on"
    STANDBY = "standby"
    OFF = "off"
    UNKNOWN = "unknown"


def normalize_power_state(value: object) -> PowerState:
    """Coerce raw payload values into the supported power-state enum."""
    if isinstance(value, PowerState):
        return value
    if isinstance(value, str):
        try:
            return PowerState(value)
        except ValueError:
            return PowerState.UNKNOWN
    return PowerState.UNKNOWN
