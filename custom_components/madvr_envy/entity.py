"""Entity base classes for madVR Envy."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from madvr_envy import exceptions

from .const import DOMAIN, MANUFACTURER, MODEL, NAME
from .coordinator import MadvrEnvyCoordinator
from .lifecycle import ConnectionState, PowerState
from .models import MadvrEnvyRuntimeState


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
            sw_version=self.snapshot.version,
            configuration_url=f"http://{self._client.host}",
        )

    @property
    def available(self) -> bool:
        return True

    @property
    def snapshot(self) -> MadvrEnvyRuntimeState:
        if self.coordinator.data is None:
            return MadvrEnvyRuntimeState()
        return self.coordinator.data

    @property
    def power_state(self) -> PowerState:
        return self.snapshot.power_state

    @property
    def connection_state(self) -> ConnectionState:
        return self.snapshot.connection_state

    @property
    def can_send_live_commands(self) -> bool:
        return self.snapshot.can_send_live_commands

    @property
    def can_wake(self) -> bool:
        return self.snapshot.can_wake

    @property
    def can_power_on(self) -> bool:
        return self.snapshot.can_power_on

    @property
    def can_power_down(self) -> bool:
        return self.snapshot.can_power_down

    @property
    def can_remote(self) -> bool:
        return self.snapshot.can_remote

    @property
    def is_awake(self) -> bool:
        return self.power_state is PowerState.ON and self.can_send_live_commands

    @property
    def _device_slug(self) -> str:
        slug = slugify(self.coordinator.device_label)
        if slug:
            return slug
        return "envy"

    async def _execute(self, command_name: str, command: Callable[[], Awaitable[Any]]) -> None:
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
