"""Runtime models for madVR Envy integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from madvr_envy import MadvrEnvyClient

from .lifecycle import ConnectionState, PowerState, WakeMode


@dataclass(slots=True)
class MadvrEnvyRuntimeState:
    """Single source of truth for the Home Assistant projection."""

    power_state: PowerState = PowerState.UNKNOWN
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    wake_mode: WakeMode = WakeMode.AUTO
    mac_address: str | None = None
    can_wake: bool = False
    can_send_live_commands: bool = False
    power_control_available: bool = False
    version: str | None = None
    current_menu: str | None = None
    aspect_ratio_mode: str | None = None
    temperatures: tuple[int, int, int, int] | None = None
    incoming_signal: dict[str, str] | None = None
    outgoing_signal: dict[str, str] | None = None
    aspect_ratio: dict[str, str | float] | None = None
    masking_ratio: dict[str, float] | None = None
    signal_present: bool | None = None
    active_profile_group: str | None = None
    active_profile_index: int | None = None
    profile_groups: dict[str, str] = field(default_factory=dict)
    profiles: dict[str, str] = field(default_factory=dict)
    tone_map_enabled: bool | None = None


@dataclass(slots=True)
class MadvrEnvyRuntimeData:
    """Stored runtime state for a config entry."""

    client: MadvrEnvyClient
    coordinator: Any
