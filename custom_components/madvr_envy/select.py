"""Select platform for madVR Envy."""

from __future__ import annotations

import re
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import MadvrEnvyEntity

_PROFILE_ID_RE = re.compile(r"^(?P<group>.+?)[_:](?P<index>\d+)$")


@dataclass(frozen=True, slots=True)
class ProfileOption:
    option: str
    group_id: str
    profile_index: int


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MadvrEnvyActiveProfileSelect(entry.runtime_data.coordinator)])


class MadvrEnvyActiveProfileSelect(MadvrEnvyEntity, SelectEntity):
    """Select active profile by group/index."""

    _attr_translation_key = "active_profile"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "active_profile")

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
                    lambda group_id=entry.group_id, profile_index=entry.profile_index: self._client.activate_profile(
                        group_id, profile_index
                    ),
                )
                return

    @property
    def _profile_options(self) -> list[ProfileOption]:
        group_names = self.data.get("profile_groups")
        if not isinstance(group_names, dict):
            group_names = {}

        profiles = self.data.get("profiles")
        if not isinstance(profiles, dict):
            return []

        options: list[ProfileOption] = []
        for profile_id, profile_name in profiles.items():
            if not isinstance(profile_id, str) or not isinstance(profile_name, str):
                continue

            parsed = _parse_profile_id(profile_id, self.data.get("active_profile_group"))
            if parsed is None:
                continue
            group_id, index = parsed

            group_label = group_names.get(group_id, group_id)
            options.append(
                ProfileOption(
                    option=f"{group_label}: {profile_name}",
                    group_id=group_id,
                    profile_index=index,
                )
            )

        options.sort(key=lambda option: option.option.casefold())
        return options


def _parse_profile_id(profile_id: str, fallback_group: object) -> tuple[str, int] | None:
    matched = _PROFILE_ID_RE.match(profile_id)
    if matched is not None:
        return matched.group("group"), int(matched.group("index"))

    if profile_id.isdigit() and isinstance(fallback_group, str):
        return fallback_group, int(profile_id)

    return None
