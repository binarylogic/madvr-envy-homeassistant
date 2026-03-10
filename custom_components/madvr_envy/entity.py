"""Entity base classes for madVR Envy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from madvr_envy import exceptions

from .const import DOMAIN, MANUFACTURER, MODEL, NAME
from .coordinator import MadvrEnvyCoordinator


class MadvrEnvyEntity(CoordinatorEntity[MadvrEnvyCoordinator]):
    """Common entity behavior for madVR Envy entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: MadvrEnvyCoordinator, entity_key: str) -> None:
        super().__init__(coordinator)
        self._entity_key = entity_key
        self._client = coordinator.client

        device_id = coordinator.device_identifier
        self._attr_unique_id = f"{device_id}_{entity_key}"
        self._attr_suggested_object_id = f"{self._device_slug}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"{NAME} ({coordinator.device_label})",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=self.data.get("version"),
            configuration_url=f"http://{self._client.host}",
        )

    @property
    def available(self) -> bool:
        return bool(self.data.get("available"))

    @property
    def _transport_available(self) -> bool:
        return bool(self.data.get("available"))

    @property
    def _power_state(self) -> str | None:
        value = self.data.get("power_state")
        if isinstance(value, str):
            return value
        return None

    @property
    def _expected_powered_down(self) -> bool:
        return self._power_state in {"standby", "off"}

    @property
    def _lifecycle_available(self) -> bool:
        return self._transport_available or self._expected_powered_down

    @property
    def data(self) -> dict[str, Any]:
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data

    @property
    def _device_slug(self) -> str:
        slug = slugify(self.coordinator.device_label)
        if slug:
            return slug
        return "envy"

    async def _execute(self, command_name: str, command: Callable[[], Any]) -> None:
        try:
            await command()
        except (
            TimeoutError,
            exceptions.NotConnectedError,
            exceptions.CommandRejectedError,
            exceptions.ConnectionFailedError,
            exceptions.ConnectionTimeoutError,
        ) as err:
            raise HomeAssistantError(f"{command_name} failed: {err}") from err
