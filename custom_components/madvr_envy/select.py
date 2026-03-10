"""Select platform for madVR Envy."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from madvr_envy.integration_bridge import ProfileOption
from madvr_envy.integration_bridge import build_profile_options as lib_build_profile_options
from madvr_envy.integration_bridge import parse_profile_id as lib_parse_profile_id

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
    _attr_options = [PowerState.ON.value, PowerState.STANDBY.value, PowerState.OFF.value]

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "power_mode")

    @property
    def available(self) -> bool:
        return self.can_power_on or self.can_power_down

    @property
    def current_option(self) -> str | None:
        if self.power_state in {PowerState.ON, PowerState.STANDBY, PowerState.OFF}:
            return self.power_state.value
        return None

    async def async_select_option(self, option: str) -> None:
        if option == PowerState.ON.value:
            await self._execute("PowerOn", self.coordinator.async_power_on)
            return
        if option == PowerState.STANDBY.value:
            await self._execute("Standby", self.coordinator.async_standby)
            return
        if option == PowerState.OFF.value:
            await self._execute("PowerOff", self.coordinator.async_power_off)


class MadvrEnvyActiveProfileSelect(MadvrEnvyEntity, SelectEntity):
    """Select active profile by group/index."""

    _attr_translation_key = "active_profile"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "active_profile")

    @property
    def available(self) -> bool:
        return True

    @property
    def options(self) -> list[str]:
        return [entry.option for entry in self._profile_options]

    @property
    def current_option(self) -> str | None:
        if not self.is_awake:
            return None
        active_group = self.snapshot.active_profile_group
        active_index = self.snapshot.active_profile_index
        if active_group is None or active_index is None:
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
        return _build_profile_options(self.snapshot.profile_groups, self.snapshot.profiles)


class MadvrEnvyProfileGroupSelect(MadvrEnvyEntity, SelectEntity):
    """Select active profile for a specific profile group."""

    _attr_icon = "mdi:playlist-edit"

    def __init__(self, coordinator, group_id: str) -> None:  # noqa: ANN001
        self._group_id = group_id
        super().__init__(coordinator, f"profile_group_{group_id}")

    @property
    def available(self) -> bool:
        return True

    @property
    def name(self) -> str:
        label = self._group_id
        value = self.snapshot.profile_groups.get(self._group_id)
        if value:
            label = value
        return f"{label} Profile"

    @property
    def options(self) -> list[str]:
        return [entry.option for entry in self._group_options]

    @property
    def current_option(self) -> str | None:
        if not self.is_awake:
            return None
        active_group = self.snapshot.active_profile_group
        active_index = self.snapshot.active_profile_index
        if active_group != self._group_id or active_index is None:
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
        all_options = _build_profile_options(self.snapshot.profile_groups, self.snapshot.profiles)
        return [entry for entry in all_options if entry.group_id == self._group_id]


def _parse_profile_id(profile_id: str, fallback_group: object) -> tuple[str, int] | None:
    return lib_parse_profile_id(profile_id, fallback_group)


def _build_profile_options(
    profile_groups: dict[str, str] | dict[str, object],
    profiles: dict[str, str] | None = None,
) -> list[ProfileOption]:
    if profiles is None:
        return lib_build_profile_options(profile_groups)
    return lib_build_profile_options(
        {
            "profile_groups": profile_groups,
            "profiles": profiles,
        }
    )


def _known_profile_group_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator,
) -> list[str]:  # noqa: ANN001
    group_ids: list[str] = []
    seen: set[str] = set()

    snapshot = coordinator.data
    if snapshot is not None:
        for group_id in snapshot.profile_groups:
            if group_id not in seen:
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
