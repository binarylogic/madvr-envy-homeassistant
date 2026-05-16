"""Runtime models for madVR Envy integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from madvr_envy import MadvrEnvyClient
from madvr_envy.runtime import EnvyDeviceSnapshot, ProfileCatalog

from .lifecycle import ConnectionState, PowerState, WakeMode


@dataclass(slots=True)
class MadvrEnvyRuntimeState:
    """Single source of truth for the Home Assistant projection."""

    device: EnvyDeviceSnapshot = field(default_factory=EnvyDeviceSnapshot)
    power_state: PowerState = PowerState.UNKNOWN
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    wake_mode: WakeMode = WakeMode.AUTO
    mac_address: str | None = None
    can_wake: bool = False
    can_send_live_commands: bool = False
    can_power_on: bool = False
    can_power_down: bool = False
    can_remote: bool = False
    profile_groups: dict[str, str] = field(default_factory=dict)

    @property
    def profiles(self) -> ProfileCatalog:
        """Return the live typed profile catalog."""
        return self.device.profiles


@dataclass(slots=True)
class MadvrEnvyRuntimeData:
    """Stored runtime state for a config entry."""

    client: MadvrEnvyClient
    coordinator: Any
