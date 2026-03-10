"""Push coordinator for madVR Envy integration."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from madvr_envy import MadvrEnvyClient
from madvr_envy import exceptions as envy_exceptions
from madvr_envy.adapter import EnvyStateAdapter
from madvr_envy.ha_bridge import HABridgeDispatcher, coordinator_payload

from .const import (
    DEFAULT_SYNC_TIMEOUT,
    DOMAIN,
)


class MadvrEnvyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Bridge madvr_envy push updates into Home Assistant entities."""

    _BOOTSTRAP_RETRY_INTERVAL_SECONDS = 5.0

    def __init__(
        self,
        hass: HomeAssistant,
        client: MadvrEnvyClient,
        *,
        sync_timeout: float = DEFAULT_SYNC_TIMEOUT,
        device_identifier: str | None = None,
        device_label: str | None = None,
    ) -> None:
        super().__init__(hass, logger=client.logger, name=DOMAIN)
        self.client = client
        self._sync_timeout = sync_timeout
        self.device_identifier = device_identifier or _default_device_identifier(client)
        self.device_label = device_label or _default_device_label(client)

        self._adapter = EnvyStateAdapter()
        self._dispatcher = HABridgeDispatcher(event_emitter=self._emit_bus_event)

        self._adapter_callback_handle: Any | None = None
        self._client_callback_registered = False
        self._started = False
        self._bootstrap_retry_task: asyncio.Task[None] | None = None

    async def async_start(self) -> None:
        """Start client and register callbacks once."""
        if self._started:
            return

        if self._adapter_callback_handle is None:
            self._adapter_callback_handle = self.client.register_adapter_callback(
                self._adapter,
                self._handle_adapter_update,
            )

        if not self._client_callback_registered:
            self.client.register_callback(self._handle_client_event)
            self._client_callback_registered = True

        self._started = True
        self.async_set_updated_data(self._with_available(False))

        try:
            await self.client.start()
            await self.client.wait_synced(timeout=self._sync_timeout)
            await self._async_publish_current_state()
        except (
            TimeoutError,
            envy_exceptions.ConnectionFailedError,
            envy_exceptions.ConnectionTimeoutError,
        ):
            self.logger.warning(
                "Initial madVR Envy bootstrap failed; keeping integration loaded and retrying in background."
            )
            self._schedule_bootstrap_retry()

    async def async_shutdown(self) -> None:
        """Stop runtime and clean callbacks."""
        if self._bootstrap_retry_task is not None:
            self._bootstrap_retry_task.cancel()
            self._bootstrap_retry_task = None

        if self._adapter_callback_handle is not None:
            self.client.deregister_adapter_callback(self._adapter_callback_handle)
            self._adapter_callback_handle = None

        if self._client_callback_registered:
            self.client.deregister_callback(self._handle_client_event)
            self._client_callback_registered = False

        await self.client.stop()
        self._started = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Return latest known data for manual refresh calls."""
        if self.data is not None:
            return deepcopy(self.data)

        snapshot, _, _ = self._adapter.update(self.client.state)
        return coordinator_payload(snapshot)

    def _emit_bus_event(self, event_type: str, event_data: dict[str, object]) -> None:
        self.hass.bus.async_fire(event_type, event_data)

    def _handle_adapter_update(self, snapshot, deltas, events) -> None:  # noqa: ANN001
        update = self._dispatcher.handle_adapter_update(snapshot, deltas, events)
        self.async_set_updated_data(update.coordinator_data)

    def _handle_client_event(self, event: str, _message: object | None = None) -> None:
        if event == "disconnected":
            self.async_set_updated_data(self._with_available(False))
        elif event == "connected":
            self.async_set_updated_data(self._with_available(self.client.state.synced))
            if not self.client.state.synced:
                self._schedule_bootstrap_retry()

    def _with_available(self, available: bool) -> dict[str, Any]:
        if self.data is not None:
            data = dict(self.data)
            data["available"] = available
            return data

        snapshot, _, _ = self._adapter.update(self.client.state)
        data = coordinator_payload(snapshot)
        data["available"] = available
        return data

    async def _prime_state(self) -> None:
        """Best-effort startup priming for richer initial entity state."""
        try:
            await self.client.get_mac_address()
            await self.client.get_temperatures()

            groups = await self.client.enum_profile_groups_collect()
            for group in groups:
                await self.client.enum_profiles_collect(group.group_id)
        except (
            TimeoutError,
            envy_exceptions.MadvrEnvyError,
            OSError,
        ) as err:
            self.logger.debug("Startup priming skipped due to command failure: %s", err)

    async def _async_publish_current_state(self) -> None:
        """Prime extra state and publish one synced snapshot."""
        await self._prime_state()
        snapshot, _, _ = self._adapter.update(self.client.state)
        self.async_set_updated_data(coordinator_payload(snapshot))

    def _schedule_bootstrap_retry(self) -> None:
        """Retry bootstrap until the client reaches a synced state."""
        if self._bootstrap_retry_task is not None and not self._bootstrap_retry_task.done():
            return
        self._bootstrap_retry_task = self.hass.async_create_background_task(
            self._async_retry_bootstrap_until_synced(),
            f"{DOMAIN} bootstrap retry",
        )

    async def _async_retry_bootstrap_until_synced(self) -> None:
        """Keep the integration loaded while the device is offline at startup."""
        try:
            while self._started and not self.client.state.synced:
                try:
                    await self.client.start()
                    await self.client.wait_synced(timeout=self._sync_timeout)
                    await self._async_publish_current_state()
                    return
                except (
                    TimeoutError,
                    envy_exceptions.ConnectionFailedError,
                    envy_exceptions.ConnectionTimeoutError,
                ):
                    await asyncio.sleep(self._BOOTSTRAP_RETRY_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            return


def _default_device_identifier(client: MadvrEnvyClient) -> str:
    """Build a stable fallback identifier when entry data is unavailable."""
    mac_address = client.state.mac_address
    if isinstance(mac_address, str) and mac_address:
        return mac_address.lower().replace(":", "")
    return f"{client.host}:{client.port}"


def _default_device_label(client: MadvrEnvyClient) -> str:
    """Build a stable fallback label when entry data is unavailable."""
    host = client.host.strip()
    if host:
        return host
    return "envy"
