"""Button platform for madVR Envy."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import OPT_ENABLE_ADVANCED_ENTITIES
from .entity import MadvrEnvyEntity


@dataclass(frozen=True, kw_only=True)
class MadvrEnvyButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[MadvrEnvyEntity], Awaitable[None]]
    live_command_only: bool = True
    power_on_command: bool = False
    power_down_command: bool = False


BUTTONS: tuple[MadvrEnvyButtonDescription, ...] = (
    MadvrEnvyButtonDescription(
        key="power_on",
        translation_key="power_on",
        icon="mdi:power-on",
        press_fn=lambda entity: entity._execute("PowerOn", entity.coordinator.async_power_on),
        live_command_only=False,
        power_on_command=True,
    ),
    MadvrEnvyButtonDescription(
        key="standby",
        translation_key="standby",
        icon="mdi:sleep",
        press_fn=lambda entity: entity._execute("Standby", entity.coordinator.async_standby),
        power_down_command=True,
    ),
    MadvrEnvyButtonDescription(
        key="power_off",
        translation_key="power_off",
        icon="mdi:power-off",
        press_fn=lambda entity: entity._execute("PowerOff", entity.coordinator.async_power_off),
        power_down_command=True,
    ),
    MadvrEnvyButtonDescription(
        key="hotplug",
        translation_key="hotplug",
        icon="mdi:video-input-hdmi",
        press_fn=lambda entity: entity._execute("Hotplug", entity._client.hotplug),
    ),
    MadvrEnvyButtonDescription(
        key="restart",
        translation_key="restart",
        icon="mdi:restart",
        press_fn=lambda entity: entity._execute("Restart", entity._client.restart),
    ),
    MadvrEnvyButtonDescription(
        key="reload_software",
        translation_key="reload_software",
        icon="mdi:update",
        press_fn=lambda entity: entity._execute("ReloadSoftware", entity._client.reload_software),
    ),
    MadvrEnvyButtonDescription(
        key="remote_menu",
        translation_key="remote_menu",
        icon="mdi:menu",
        press_fn=lambda entity: entity._execute(
            "KeyPress MENU", lambda: entity._client.key_press("MENU")
        ),
    ),
    MadvrEnvyButtonDescription(
        key="remote_info",
        translation_key="remote_info",
        icon="mdi:information",
        press_fn=lambda entity: entity._execute(
            "KeyPress INFO", lambda: entity._client.key_press("INFO")
        ),
    ),
    MadvrEnvyButtonDescription(
        key="remote_ok",
        translation_key="remote_ok",
        icon="mdi:check-circle-outline",
        press_fn=lambda entity: entity._execute(
            "KeyPress OK", lambda: entity._client.key_press("OK")
        ),
    ),
    MadvrEnvyButtonDescription(
        key="remote_back",
        translation_key="remote_back",
        icon="mdi:arrow-left-circle-outline",
        press_fn=lambda entity: entity._execute(
            "KeyPress BACK", lambda: entity._client.key_press("BACK")
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    enable_advanced = entry.options.get(OPT_ENABLE_ADVANCED_ENTITIES, True)
    coordinator = entry.runtime_data.coordinator

    entities: list[MadvrEnvyButton] = []
    for description in BUTTONS:
        if description.key.startswith("remote_") and not enable_advanced:
            continue
        entities.append(MadvrEnvyButton(coordinator, description))

    async_add_entities(entities)


class MadvrEnvyButton(MadvrEnvyEntity, ButtonEntity):
    """madVR Envy button."""

    entity_description: MadvrEnvyButtonDescription

    def __init__(self, coordinator, description: MadvrEnvyButtonDescription) -> None:  # noqa: ANN001
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if self.entity_description.power_on_command:
            return self.can_power_on
        if self.entity_description.power_down_command:
            return self.can_power_down
        if self.entity_description.live_command_only:
            return self.can_send_live_commands
        return True

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self)
