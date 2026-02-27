"""Remote platform for madVR Envy."""

from __future__ import annotations

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import MadvrEnvyEntity


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
    def is_on(self) -> bool:
        return self.available and self.data.get("power_state") != "off"

    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        await self._execute("KeyPress POWER", lambda: self._client.key_press("POWER"))

    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003
        await self._execute("Standby", self._client.standby)

    async def async_send_command(self, command, **kwargs) -> None:  # noqa: ANN001, ANN003
        commands = [command] if isinstance(command, str) else command
        for item in commands:
            if not isinstance(item, str):
                continue
            key = item.strip()
            if not key:
                continue
            if key.startswith("action:"):
                await self._run_action(key.split(":", 1)[1])
            else:
                await self._execute(
                    f"KeyPress {key}", lambda button=key: self._client.key_press(button)
                )

    async def _run_action(self, action: str) -> None:
        action_name = action.strip().lower()
        actions = {
            "standby": self._client.standby,
            "power_off": self._client.power_off,
            "hotplug": self._client.hotplug,
            "restart": self._client.restart,
            "reload_software": self._client.reload_software,
            "tone_map_on": self._client.tone_map_on,
            "tone_map_off": self._client.tone_map_off,
        }
        command = actions.get(action_name)
        if command is not None:
            await self._execute(action_name, command)
