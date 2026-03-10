"""Select platform for madVR Envy."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from madvr_envy.integration_bridge import (
    ProfileOption,
)
from madvr_envy.integration_bridge import (
    build_profile_options as lib_build_profile_options,
)
from madvr_envy.integration_bridge import (
    parse_profile_id as lib_parse_profile_id,
)

from .entity import MadvrEnvyEntity
from .lifecycle import PowerState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[MadvrEnvyEntity] = [
        MadvrEnvyPowerModeSelect(coordinator),
        MadvrEnvyActiveProfileSelect(coordinator),
    ]

    for group_id in _known_profile_group_ids(hass, entry, coordinator):
        entities.append(MadvrEnvyProfileGroupSelect(coordinator, group_id))

    async_add_entities(entities)


class MadvrEnvyPowerModeSelect(MadvrEnvyEntity, SelectEntity):
    """Select target power mode."""

    _attr_translation_key = "power_mode"
    _attr_icon = "mdi:power-settings"
    _attr_options = ["on", "standby", "off"]

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "power_mode")

    @property
    def available(self) -> bool:
        return self._entity_state_available

    @property
    def current_option(self) -> str | None:
        power_state = self.data.get("power_state")
        if isinstance(power_state, str) and power_state in self.options:
            return power_state
        return None

    async def async_select_option(self, option: str) -> None:
        if option == "on":
            await self._execute_with_power_state(
                "KeyPress POWER",
                None,
                lambda: self._client.key_press("POWER"),
            )
            return
        if option == "standby":
            await self._execute_with_power_state(
                "Standby",
                PowerState.STANDBY,
                self._client.standby,
            )
            return
        if option == "off":
            await self._execute_with_power_state(
                "PowerOff",
                PowerState.OFF,
                self._client.power_off,
            )


class MadvrEnvyActiveProfileSelect(MadvrEnvyEntity, SelectEntity):
    """Select active profile by group/index."""

    _attr_translation_key = "active_profile"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "active_profile")

    @property
    def available(self) -> bool:
        return self._entity_state_available

    @property
    def options(self) -> list[str]:
        return [entry.option for entry in self._profile_options]

    @property
    def current_option(self) -> str | None:
        active_group = self.data.get("active_profile_group")
        active_index = self.data.get("active_profile_index")
        if not isinstance(active_group, str) or not isinstance(active_index, int):
            return None

        for entry in self._profile_options:
            if entry.group_id == active_group and entry.profile_index == active_index:
                return entry.option
        return None

    async def async_select_option(self, option: str) -> None:
        for entry in self._profile_options:
            if entry.option == option:
                await self._execute(
                    f"ActivateProfile {entry.group_id}/{entry.profile_index}",
                    lambda group_id=entry.group_id, profile_index=entry.profile_index: (
                        self._client.activate_profile(group_id, profile_index)
                    ),
                )
                return

    @property
    def _profile_options(self) -> list[ProfileOption]:
        return _build_profile_options(self.data)


class MadvrEnvyProfileGroupSelect(MadvrEnvyEntity, SelectEntity):
    """Select active profile for a specific profile group."""

    _attr_icon = "mdi:playlist-edit"

    def __init__(self, coordinator, group_id: str) -> None:  # noqa: ANN001
        self._group_id = group_id
        super().__init__(coordinator, f"profile_group_{group_id}")

    @property
    def available(self) -> bool:
        return self._entity_state_available

    @property
    def name(self) -> str:
        group_names = self.data.get("profile_groups")
        label = self._group_id
        if not isinstance(group_names, dict):
            return f"{label} Profile"
        value = group_names.get(self._group_id)
        if isinstance(value, str) and value:
            label = value
        return f"{label} Profile"

    @property
    def options(self) -> list[str]:
        return [entry.option for entry in self._group_options]

    @property
    def current_option(self) -> str | None:
        active_group = self.data.get("active_profile_group")
        active_index = self.data.get("active_profile_index")
        if active_group != self._group_id or not isinstance(active_index, int):
            return None
        for entry in self._group_options:
            if entry.profile_index == active_index:
                return entry.option
        return None

    async def async_select_option(self, option: str) -> None:
        for entry in self._group_options:
            if entry.option != option:
                continue
            await self._execute(
                f"ActivateProfile {self._group_id}/{entry.profile_index}",
                lambda profile_index=entry.profile_index: self._client.activate_profile(
                    self._group_id, profile_index
                ),
            )
            return

    @property
    def _group_options(self) -> list[ProfileOption]:
        all_options = _build_profile_options(self.data)
        return [entry for entry in all_options if entry.group_id == self._group_id]


def _parse_profile_id(profile_id: str, fallback_group: object) -> tuple[str, int] | None:
    return lib_parse_profile_id(profile_id, fallback_group)


def _build_profile_options(data: dict[str, object]) -> list[ProfileOption]:
    return lib_build_profile_options(data)


def _known_profile_group_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator,
) -> list[str]:  # noqa: ANN001
    group_ids: list[str] = []
    seen: set[str] = set()

    profile_groups = coordinator.data.get("profile_groups", {}) if coordinator.data else {}
    if isinstance(profile_groups, dict):
        for group_id in profile_groups:
            if isinstance(group_id, str) and group_id not in seen:
                seen.add(group_id)
                group_ids.append(group_id)

    entry_id = getattr(entry, "entry_id", None)
    if entry_id is not None:
        registry = er.async_get(hass)
        prefix = f"{coordinator.device_identifier}_profile_group_"
        for registry_entry in er.async_entries_for_config_entry(registry, entry_id):
            unique_id = registry_entry.unique_id
            if not unique_id.startswith(prefix):
                continue
            group_id = unique_id.removeprefix(prefix)
            if group_id and group_id not in seen:
                seen.add(group_id)
                group_ids.append(group_id)

    return group_ids
