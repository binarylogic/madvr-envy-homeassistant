"""Persistent runtime storage for madVR Envy."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .lifecycle import RestoredRuntimeState, normalize_mac_address, normalize_power_state

_STORAGE_VERSION = 1


class MadvrEnvyStore:
    """Persist lifecycle state that must survive HA restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.runtime")

    async def async_load(self) -> RestoredRuntimeState:
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return RestoredRuntimeState()

        profile_groups = data.get("profile_groups")
        profiles = data.get("profiles")
        return RestoredRuntimeState(
            power_state=normalize_power_state(data.get("power_state")),
            mac_address=normalize_mac_address(data.get("mac_address")),
            profile_groups=dict(profile_groups) if isinstance(profile_groups, dict) else {},
            profiles=dict(profiles) if isinstance(profiles, dict) else {},
        )

    async def async_save(self, state: RestoredRuntimeState) -> None:
        payload = asdict(state)
        payload["power_state"] = state.power_state.value
        await self._store.async_save(payload)
