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
        value_fn=lambda snapshot: (
            snapshot.device.temperatures.gpu if snapshot.device.temperatures else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="hdmi_input_temperature",
        translation_key="hdmi_input_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda snapshot: (
            snapshot.device.temperatures.hdmi_input if snapshot.device.temperatures else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="cpu_temperature",
        translation_key="cpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda snapshot: (
            snapshot.device.temperatures.cpu if snapshot.device.temperatures else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="mainboard_temperature",
        translation_key="mainboard_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda snapshot: (
            snapshot.device.temperatures.mainboard if snapshot.device.temperatures else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="version",
        translation_key="version",
        icon="mdi:identifier",
        entity_registry_enabled_default=False,
        value_fn=lambda snapshot: snapshot.device.version,
    ),
    MadvrEnvySensorDescription(
        key="current_menu",
        translation_key="current_menu",
        icon="mdi:menu",
        entity_registry_enabled_default=False,
        value_fn=lambda snapshot: snapshot.device.current_menu,
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_resolution",
        translation_key="incoming_signal_resolution",
        icon="mdi:video-input-hdmi",
        value_fn=lambda snapshot: (
            snapshot.device.incoming_signal.resolution if snapshot.device.incoming_signal else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_frame_rate",
        translation_key="incoming_signal_frame_rate",
        icon="mdi:speedometer",
        value_fn=lambda snapshot: (
            snapshot.device.incoming_signal.frame_rate if snapshot.device.incoming_signal else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_aspect_ratio",
        translation_key="incoming_signal_aspect_ratio",
        icon="mdi:aspect-ratio",
        value_fn=lambda snapshot: (
            snapshot.device.incoming_signal.aspect_ratio
            if snapshot.device.incoming_signal
            else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="incoming_signal_hdr_mode",
        translation_key="incoming_signal_hdr_mode",
        icon="mdi:brightness-6",
        value_fn=lambda snapshot: (
            snapshot.device.incoming_signal.hdr_mode if snapshot.device.incoming_signal else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="outgoing_signal_resolution",
        translation_key="outgoing_signal_resolution",
        icon="mdi:video-output",
        value_fn=lambda snapshot: (
            snapshot.device.outgoing_signal.resolution if snapshot.device.outgoing_signal else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="outgoing_signal_frame_rate",
        translation_key="outgoing_signal_frame_rate",
        icon="mdi:speedometer-medium",
        value_fn=lambda snapshot: (
            snapshot.device.outgoing_signal.frame_rate if snapshot.device.outgoing_signal else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="outgoing_signal_hdr_mode",
        translation_key="outgoing_signal_hdr_mode",
        icon="mdi:brightness-5",
        value_fn=lambda snapshot: (
            snapshot.device.outgoing_signal.hdr_mode if snapshot.device.outgoing_signal else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="aspect_ratio_name",
        translation_key="aspect_ratio_name",
        icon="mdi:format-letter-case",
        value_fn=lambda snapshot: (
            snapshot.device.video.aspect_ratio.name
            if snapshot.device.video.trusted and snapshot.device.video.aspect_ratio
            else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="aspect_ratio_decimal",
        translation_key="aspect_ratio_decimal",
        icon="mdi:aspect-ratio",
        value_fn=lambda snapshot: (
            snapshot.device.video.aspect_ratio.decimal_ratio
            if snapshot.device.video.trusted and snapshot.device.video.aspect_ratio
            else None
        ),
    ),
    MadvrEnvySensorDescription(
        key="masking_ratio_decimal",
        translation_key="masking_ratio_decimal",
        icon="mdi:crop",
        value_fn=lambda snapshot: (
            snapshot.device.video.masking_ratio.decimal_ratio
            if snapshot.device.video.trusted and snapshot.device.video.masking_ratio
            else None
        ),
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
    def available(self) -> bool:
        if self.entity_description.key == "power_state":
            return True
        return self.is_awake

    @property
    def native_value(self) -> Any:
        if self.entity_description.key == "power_state":
            return self.power_state.value
        if not self.is_awake:
            return None
        return self.entity_description.value_fn(self.snapshot)
