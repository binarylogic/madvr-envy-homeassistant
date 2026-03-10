"""Remote platform for madVR Envy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from madvr_envy.integration_bridge import iter_remote_operations, resolve_action_method

from .entity import MadvrEnvyEntity
from .lifecycle import PowerState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MadvrEnvyRemote(entry.runtime_data.coordinator)])


class MadvrEnvyRemote(MadvrEnvyEntity, RemoteEntity):
    """Remote command entity for madVR Envy."""

    _attr_translation_key = "remote"

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "remote")

    @property
    def available(self) -> bool:
        return self.power_control_available

    @property
    def is_on(self) -> bool:
        return self.power_state is PowerState.ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._execute("PowerOn", self.coordinator.async_power_on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._execute("Standby", self.coordinator.async_standby)

    async def async_send_command(self, command: Any, **kwargs: Any) -> None:
        for operation in iter_remote_operations(command):
            if operation.kind == "action":
                await self._run_action(operation.value)
                continue

            key = operation.value
            await self._execute(
                f"KeyPress {key}", lambda button=key: self._client.key_press(button)
            )

    async def _run_action(self, action: str) -> None:
        try:
            command = resolve_action_method(self._client, action)
        except ValueError:
            return
        await self._execute(action.strip().lower(), command)
