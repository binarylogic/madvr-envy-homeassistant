"""Sensor platform for madVR Envy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import OPT_ENABLE_ADVANCED_ENTITIES
from .entity import MadvrEnvyEntity
from .lifecycle import PowerState
from .models import MadvrEnvyRuntimeState


@dataclass(frozen=True, kw_only=True)
class MadvrEnvySensorDescription(SensorEntityDescription):
    value_fn: Any


SENSORS: tuple[MadvrEnvySensorDescription, ...] = (
    MadvrEnvySensorDescription(
        key="power_state",
        translation_key="power_state",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:power",
        options=[state.value for state in PowerState],
        value_fn=lambda snapshot: snapshot.power_state.value,
    ),
    MadvrEnvySensorDescription(
        key="gpu_temperature",
        translation_key="gpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda snapshot: _temperature_value(snapshot, 0),
    ),
    MadvrEnvySensorDescription(
        key="hdmi_input_temperature",
        translation_key="hdmi_input_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda snapshot: _temperature_value(snapshot, 1),
    ),
    MadvrEnvySensorDescription(
        key="cpu_temperature",
        translation_key="cpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda snapshot: _temperature_value(snapshot, 2),
    ),
    MadvrEnvySensorDescription(
        key="mainboard_temperature",
        translation_key="mainboard_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda snapshot: _temperature_value(snapshot, 3),
    ),
    MadvrEnvySensorDescription(
        key="version",
        translation_key="version",
        icon="mdi:identifier",
        entity_registry_enabled_default=False,
        value_fn=lambda snapshot: snapshot.version,
    ),
    MadvrEnvySensorDescription(
        key="current_menu",
        translation_key="current_menu",
        icon="mdi:menu",
        entity_registry_enabled_default=False,
        value_fn=lambda snapshot: snapshot.current_menu,
    ),
    MadvrEnvySensorDescription(
        key="aspect_ratio_mode",
        translation_key="aspect_ratio_mode",
        icon="mdi:aspect-ratio",
        value_fn=lambda snapshot: snapshot.aspect_ratio_mode,
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_resolution",
        translation_key="incoming_signal_resolution",
        icon="mdi:video-input-hdmi",
        value_fn=lambda snapshot: _nested_value(snapshot.incoming_signal, "resolution"),
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_frame_rate",
        translation_key="incoming_signal_frame_rate",
        icon="mdi:speedometer",
        value_fn=lambda snapshot: _nested_value(snapshot.incoming_signal, "frame_rate"),
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_aspect_ratio",
        translation_key="incoming_signal_aspect_ratio",
        icon="mdi:aspect-ratio",
        value_fn=lambda snapshot: _nested_value(snapshot.incoming_signal, "aspect_ratio"),
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_hdr_mode",
        translation_key="incoming_signal_hdr_mode",
        icon="mdi:brightness-6",
        value_fn=lambda snapshot: _nested_value(snapshot.incoming_signal, "hdr_mode"),
    ),
    MadvrEnvySensorDescription(
        key="outgoing_signal_resolution",
        translation_key="outgoing_signal_resolution",
        icon="mdi:video-output",
        value_fn=lambda snapshot: _nested_value(snapshot.outgoing_signal, "resolution"),
    ),
    MadvrEnvySensorDescription(
        key="outgoing_signal_frame_rate",
        translation_key="outgoing_signal_frame_rate",
        icon="mdi:speedometer-medium",
        value_fn=lambda snapshot: _nested_value(snapshot.outgoing_signal, "frame_rate"),
    ),
    MadvrEnvySensorDescription(
        key="outgoing_signal_hdr_mode",
        translation_key="outgoing_signal_hdr_mode",
        icon="mdi:brightness-5",
        value_fn=lambda snapshot: _nested_value(snapshot.outgoing_signal, "hdr_mode"),
    ),
    MadvrEnvySensorDescription(
        key="aspect_ratio_name",
        translation_key="aspect_ratio_name",
        icon="mdi:format-letter-case",
        value_fn=lambda snapshot: _nested_value(snapshot.aspect_ratio, "name"),
    ),
    MadvrEnvySensorDescription(
        key="aspect_ratio_decimal",
        translation_key="aspect_ratio_decimal",
        icon="mdi:aspect-ratio",
        value_fn=lambda snapshot: _ratio_decimal_value(snapshot.aspect_ratio),
    ),
    MadvrEnvySensorDescription(
        key="masking_ratio_decimal",
        translation_key="masking_ratio_decimal",
        icon="mdi:crop",
        value_fn=lambda snapshot: _ratio_decimal_value(snapshot.masking_ratio),
    ),
    MadvrEnvySensorDescription(
        key="active_profile",
        translation_key="active_profile",
        icon="mdi:playlist-play",
        value_fn=lambda snapshot: _active_profile_value(snapshot),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    enable_advanced = entry.options.get(OPT_ENABLE_ADVANCED_ENTITIES, True)
    entities: list[MadvrEnvySensor] = []

    for description in SENSORS:
        if description.key in {"version", "current_menu"} and not enable_advanced:
            continue
        entities.append(MadvrEnvySensor(entry.runtime_data.coordinator, description))

    async_add_entities(entities)


class MadvrEnvySensor(MadvrEnvyEntity, SensorEntity):
    """madVR Envy sensor."""

    entity_description: MadvrEnvySensorDescription

    def __init__(self, coordinator, description: MadvrEnvySensorDescription) -> None:  # noqa: ANN001
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if self.entity_description.key == "power_state":
            return self.power_state.value
        if not self.is_awake:
            return None
        return self.entity_description.value_fn(self.snapshot)


def _temperature_value(snapshot: MadvrEnvyRuntimeState, index: int) -> int | None:
    temperatures = snapshot.temperatures
    if temperatures is None:
        return None
    if len(temperatures) <= index:
        return None

    value = temperatures[index]
    if isinstance(value, int):
        return value
    return None


def _active_profile_value(snapshot: MadvrEnvyRuntimeState) -> str | None:
    group = snapshot.active_profile_group
    index = snapshot.active_profile_index
    if group is None or index is None:
        return None

    group_name = group
    value = snapshot.profile_groups.get(group)
    if value:
        group_name = value

    profile_name = str(index)
    key = f"{group}_{index}"
    value = snapshot.profiles.get(key)
    if value:
        profile_name = value

    return f"{group_name}: {profile_name}"


def _nested_value(data: dict[str, str] | dict[str, str | float] | None, nested_key: str) -> str | None:
    if data is None:
        return None
    value = data.get(nested_key)
    if isinstance(value, str):
        return value
    return None


def _ratio_decimal_value(ratio: dict[str, str | float] | dict[str, float] | None) -> float | None:
    if ratio is None:
        return None
    value = ratio.get("decimal_ratio")
    if isinstance(value, (int, float)):
        return float(value)
    return None
