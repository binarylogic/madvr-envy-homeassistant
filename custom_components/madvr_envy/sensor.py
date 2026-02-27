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


@dataclass(frozen=True, kw_only=True)
class MadvrEnvySensorDescription(SensorEntityDescription):
    value_fn: Any


SENSORS: tuple[MadvrEnvySensorDescription, ...] = (
    MadvrEnvySensorDescription(
        key="power_state",
        translation_key="power_state",
        icon="mdi:power",
        value_fn=lambda data: data.get("power_state"),
    ),
    MadvrEnvySensorDescription(
        key="gpu_temperature",
        translation_key="gpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: _temperature_value(data, 0),
    ),
    MadvrEnvySensorDescription(
        key="hdmi_input_temperature",
        translation_key="hdmi_input_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: _temperature_value(data, 1),
    ),
    MadvrEnvySensorDescription(
        key="cpu_temperature",
        translation_key="cpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: _temperature_value(data, 2),
    ),
    MadvrEnvySensorDescription(
        key="mainboard_temperature",
        translation_key="mainboard_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: _temperature_value(data, 3),
    ),
    MadvrEnvySensorDescription(
        key="version",
        translation_key="version",
        icon="mdi:identifier",
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("version"),
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
        if description.key == "version" and not enable_advanced:
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
        return self.entity_description.value_fn(self.data)


def _temperature_value(data: dict[str, Any], index: int) -> int | None:
    temperatures = data.get("temperatures")
    if not isinstance(temperatures, (tuple, list)):
        return None
    if len(temperatures) <= index:
        return None

    value = temperatures[index]
    if isinstance(value, int):
        return value
    return None
