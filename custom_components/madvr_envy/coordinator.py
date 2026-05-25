"""Push coordinator for madVR Envy integration."""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from madvr_envy import MadvrEnvyClient
from madvr_envy import exceptions as envy_exceptions
from madvr_envy.protocol import DisplayChangedMessage, PowerOffMessage, StandbyMessage
from madvr_envy.runtime import EnvyDeviceSnapshot

from .const import DEFAULT_SYNC_TIMEOUT, DOMAIN
from .lifecycle import (
    ConnectionState,
    PowerState,
    RestoredRuntimeState,
    WakeMode,
    normalize_mac_address,
)
from .models import MadvrEnvyRuntimeState
from .store import MadvrEnvyStore
from .wol import async_send_magic_packet


class MadvrEnvyCoordinator(DataUpdateCoordinator[MadvrEnvyRuntimeState]):
    """Bridge madVR Envy push updates into a stable HA runtime model."""

    _BOOTSTRAP_RETRY_INTERVAL_SECONDS = 5.0
    _VIDEO_GEOMETRY_REFRESH_DELAY_SECONDS = 0.75

    def __init__(
        self,
        hass: HomeAssistant,
        client: MadvrEnvyClient,
        *,
        entry_id: str,
        sync_timeout: float = DEFAULT_SYNC_TIMEOUT,
        device_identifier: str | None = None,
        device_label: str | None = None,
        configured_mac_address: str | None = None,
        wake_mode: WakeMode = WakeMode.AUTO,
    ) -> None:
        super().__init__(hass, logger=client.logger, name=DOMAIN)
        self.client = client
        self._sync_timeout = sync_timeout
        self.device_identifier = device_identifier or _default_device_identifier(client)
        self.device_label = device_label or _default_device_label(client)
        self._store = MadvrEnvyStore(hass, entry_id)
        self._wake_mode = wake_mode

        self._client_callback_registered = False
        self._started = False
        self._bootstrap_retry_task: asyncio.Task[None] | None = None
        self._activation_retry_task: asyncio.Task[None] | None = None
        self._video_geometry_refresh_task: asyncio.Task[None] | None = None
        self._save_task: asyncio.Task[None] | None = None
        self._activation_live_power_sent = False

        self._connection_state = ConnectionState.DISCONNECTED
        self._power_state = PowerState.UNKNOWN
        self._mac_address = normalize_mac_address(configured_mac_address)
        self._profile_groups: dict[str, str] = {}
        self._device_snapshot = EnvyDeviceSnapshot()

    async def async_start(self) -> None:
        """Start client and register callbacks once."""
        if self._started:
            return

        self.client.auto_reconnect = True

        restored = await self._store.async_load()
        self._apply_restored_state(restored)

        if not self._client_callback_registered:
            self.client.register_callback(self._handle_client_event)
            self._client_callback_registered = True

        self._started = True
        self._publish()

        try:
            await self.client.start()
            await self.client.wait_synced(timeout=self._sync_timeout)
            self._connection_state = ConnectionState.CONNECTED
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

        if self._activation_retry_task is not None:
            self._activation_retry_task.cancel()
            self._activation_retry_task = None

        if self._video_geometry_refresh_task is not None:
            self._video_geometry_refresh_task.cancel()
            self._video_geometry_refresh_task = None

        if self._save_task is not None:
            self._save_task.cancel()
            self._save_task = None

        if self._client_callback_registered:
            self.client.deregister_callback(self._handle_client_event)
            self._client_callback_registered = False

        await self._async_stop_client_safely()
        self._started = False

    async def _async_update_data(self) -> MadvrEnvyRuntimeState:
        """Return latest known data for manual refresh calls."""
        return self._build_data()

    @property
    def power_state(self) -> PowerState:
        """Return the current primary lifecycle state."""
        return self._power_state

    @property
    def connection_state(self) -> ConnectionState:
        """Return the current transport state."""
        return self._connection_state

    @property
    def wake_mode(self) -> WakeMode:
        """Return the configured wake behavior."""
        return self._wake_mode

    @property
    def mac_address(self) -> str | None:
        """Return the normalized MAC address used for wake-on-LAN."""
        return self._mac_address

    @property
    def can_send_live_commands(self) -> bool:
        """Return whether the Envy is currently reachable for live commands."""
        return self._connection_state is ConnectionState.CONNECTED and self.client.state.synced

    @property
    def can_wake(self) -> bool:
        """Return whether Home Assistant has a wake path for the device."""
        if self.can_send_live_commands:
            return True
        if self._wake_mode is WakeMode.NONE:
            return False
        if self._wake_mode is WakeMode.IP:
            return False
        return self._mac_address is not None

    @property
    def power_control_available(self) -> bool:
        """Return whether at least one power control is meaningful now."""
        return self.can_send_live_commands or self.can_wake

    @property
    def can_power_on(self) -> bool:
        """Return whether a wake/power-on action can succeed now."""
        return self.can_send_live_commands or self.can_wake

    @property
    def can_power_down(self) -> bool:
        """Return whether standby/power-off commands can succeed now."""
        return self.can_send_live_commands

    @property
    def can_remote(self) -> bool:
        """Return whether remote control commands can succeed now."""
        return self.can_send_live_commands

    async def async_power_on(self) -> None:
        """Send the Envy live power-on command over the active transport."""
        self.client.auto_reconnect = True
        await self.client.power_on()

    async def async_ensure_on(self) -> None:
        """Ensure the device wakes using the configured activation path."""
        self.client.auto_reconnect = True
        if self._power_state is PowerState.ON:
            return
        if self._activation_retry_task is not None and not self._activation_retry_task.done():
            if self._wake_mode is not WakeMode.NONE and self._mac_address is not None:
                await async_send_magic_packet(self._mac_address, self.client.host)
            return

        self._activation_live_power_sent = False

        if await self._async_wake_once():
            return

        if not self.can_wake:
            raise envy_exceptions.NotConnectedError("No wake path configured")

        self._schedule_activation_retry()

    async def _async_wake_once(self) -> bool:
        """Run one explicit wake pass without surfacing expected sleep/off races."""
        if self._wake_mode is not WakeMode.NONE and self._mac_address is not None:
            await async_send_magic_packet(self._mac_address, self.client.host)

        if self.can_send_live_commands:
            await self._async_publish_current_state()
            if self._power_state is PowerState.ON:
                return True
            await self._async_send_power_on_over_live_transport()
            if await self._async_connect_and_publish_until_synced():
                return self._power_state is PowerState.ON
            return False

        if await self._async_send_power_on_over_live_transport():
            if await self._async_connect_and_publish_until_synced():
                return self._power_state is PowerState.ON
            return False

        if await self._async_connect_and_publish_until_synced():
            if self._power_state is PowerState.ON:
                return True
            if self.can_send_live_commands:
                await self._async_send_power_on_over_live_transport()
                if await self._async_connect_and_publish_until_synced():
                    return self._power_state is PowerState.ON

        return False

    async def async_standby(self) -> None:
        """Put the device into standby."""
        await self._async_apply_sleep_transition(
            self.client.standby,
            target_state=PowerState.STANDBY,
            protocol_message=StandbyMessage(),
        )

    async def async_power_off(self) -> None:
        """Turn the device fully off."""
        await self._async_apply_sleep_transition(
            self.client.power_off,
            target_state=PowerState.OFF,
            protocol_message=PowerOffMessage(),
        )

    def _handle_client_event(self, event: str, message: object | None = None) -> None:
        if event == "disconnected":
            self._connection_state = ConnectionState.DISCONNECTED
            if self._power_state is PowerState.ON:
                self._power_state = PowerState.UNKNOWN
            self._device_snapshot = self.client.device_snapshot
            self._publish()
        elif event == "connected":
            self._connection_state = ConnectionState.CONNECTED
            self._device_snapshot = self.client.device_snapshot
            self._publish()
            if not self.client.state.synced:
                self._schedule_bootstrap_retry()
        elif event == "received_message":
            self._device_snapshot = self.client.device_snapshot
            self._sync_power_state_from_device()
            self._sync_profile_groups_from_device()
            self._publish()
            if isinstance(message, DisplayChangedMessage):
                self._schedule_video_geometry_refresh()

    async def _async_publish_current_state(self) -> None:
        """Refresh semantic device state and publish one synced snapshot."""
        try:
            self._device_snapshot = await self.client.refresh_device()
        except (
            TimeoutError,
            envy_exceptions.MadvrEnvyError,
            OSError,
        ) as err:
            self.logger.debug("Device refresh incomplete: %s", err)
            self._device_snapshot = self.client.device_snapshot
        self._sync_power_state_from_device()
        self._sync_profile_groups_from_device()
        self._publish()

    def _apply_restored_state(self, restored: RestoredRuntimeState) -> None:
        if restored.power_state in (PowerState.STANDBY, PowerState.OFF):
            self._power_state = restored.power_state
        else:
            self._power_state = PowerState.UNKNOWN
        self._profile_groups = dict(restored.profile_groups or {})

    def _sync_power_state_from_device(self) -> None:
        power_state = self._device_snapshot.power_state
        if power_state is not PowerState.UNKNOWN and (
            self._connection_state is ConnectionState.CONNECTED
            or power_state in (PowerState.STANDBY, PowerState.OFF)
        ):
            self._power_state = power_state
            if power_state is PowerState.ON:
                self._activation_live_power_sent = False

    def _sync_profile_groups_from_device(self) -> None:
        groups = {group.group_id: group.name for group in self._device_snapshot.profiles.groups}
        if groups:
            self._profile_groups = groups

    def _publish(self) -> None:
        self.async_set_updated_data(self._build_data())
        self._schedule_save()

    def _build_data(self) -> MadvrEnvyRuntimeState:
        return MadvrEnvyRuntimeState(
            device=self._device_snapshot,
            power_state=self._power_state,
            connection_state=self._connection_state,
            wake_mode=self._wake_mode,
            mac_address=self._mac_address,
            can_wake=self.can_wake,
            can_send_live_commands=self.can_send_live_commands,
            can_power_on=self.can_power_on,
            can_power_down=self.can_power_down,
            can_remote=self.can_remote,
            profile_groups=dict(self._profile_groups),
        )

    def _schedule_save(self) -> None:
        if self._save_task is not None and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = self.hass.async_create_background_task(
            self._store.async_save(
                RestoredRuntimeState(
                    power_state=self._power_state,
                    mac_address=self._mac_address,
                    profile_groups=dict(self._profile_groups),
                )
            ),
            f"{DOMAIN} persist runtime",
        )

    def _schedule_bootstrap_retry(self) -> None:
        """Retry bootstrap until the client reaches a synced state."""
        if self._bootstrap_retry_task is not None and not self._bootstrap_retry_task.done():
            return
        self._bootstrap_retry_task = self.hass.async_create_background_task(
            self._async_retry_bootstrap_until_synced(),
            f"{DOMAIN} bootstrap retry",
        )

    def _schedule_activation_retry(self) -> None:
        """Retry activation intent until the Envy reports on or the wake window expires."""
        if self._activation_retry_task is not None and not self._activation_retry_task.done():
            return
        self._activation_retry_task = self.hass.async_create_background_task(
            self._async_retry_activation_until_on(),
            f"{DOMAIN} activation retry",
        )

    def _schedule_video_geometry_refresh(self) -> None:
        """Refresh aspect/masking after display geometry settles."""
        if (
            self._video_geometry_refresh_task is not None
            and not self._video_geometry_refresh_task.done()
        ):
            self._video_geometry_refresh_task.cancel()
        self._video_geometry_refresh_task = self.hass.async_create_background_task(
            self._async_refresh_video_geometry_after_delay(),
            f"{DOMAIN} video geometry refresh",
        )

    async def _async_refresh_video_geometry_after_delay(self) -> None:
        """Debounce geometry changes and publish freshly queried aspect/masking state."""
        try:
            await asyncio.sleep(self._VIDEO_GEOMETRY_REFRESH_DELAY_SECONDS)
            if not self.can_send_live_commands:
                return
            self._device_snapshot = await self.client.refresh_video_geometry()
            self._sync_power_state_from_device()
            self._publish()
        except asyncio.CancelledError:
            return
        except (TimeoutError, envy_exceptions.MadvrEnvyError, OSError) as err:
            self.logger.debug("Video geometry refresh incomplete: %s", err)

    async def _async_retry_bootstrap_until_synced(self) -> None:
        """Keep the integration loaded while the device is offline at startup."""
        try:
            while self._started and not self.can_send_live_commands:
                if await self._async_connect_and_publish_until_synced():
                    return
                await asyncio.sleep(self._BOOTSTRAP_RETRY_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            return

    async def _async_retry_activation_until_on(self) -> None:
        """Keep applying activation intent while the Envy wakes from standby/off."""
        deadline = self.hass.loop.time() + 180
        try:
            while self._started and self._power_state is not PowerState.ON:
                if await self._async_wake_once():
                    return
                if self.hass.loop.time() >= deadline:
                    return
                await asyncio.sleep(self._BOOTSTRAP_RETRY_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            return

    async def _async_connect_and_publish_until_synced(self) -> bool:
        """Try one transport bootstrap cycle and publish a fresh device snapshot."""
        try:
            await self.client.start()
            await self.client.wait_synced(timeout=self._sync_timeout)
        except (
            TimeoutError,
            envy_exceptions.ConnectionFailedError,
            envy_exceptions.ConnectionTimeoutError,
            envy_exceptions.NotConnectedError,
            OSError,
        ):
            self._connection_state = ConnectionState.DISCONNECTED
            self._device_snapshot = self.client.device_snapshot
            self._publish()
            return False

        self._connection_state = ConnectionState.CONNECTED
        await self._async_publish_current_state()
        return self.can_send_live_commands

    async def _async_send_power_on_over_live_transport(self) -> bool:
        """Send one POWER pulse for the active wake intent if TCP is reachable."""
        if self._activation_live_power_sent:
            return False
        try:
            await self.client.start()
            if not self.client.connected:
                return False
            await self.client.power_on(wait_for_ack=False)
            self._activation_live_power_sent = True
            return True
        except (
            TimeoutError,
            envy_exceptions.ConnectionFailedError,
            envy_exceptions.ConnectionTimeoutError,
            envy_exceptions.NotConnectedError,
            OSError,
        ) as err:
            self.logger.debug("Best-effort Envy POWER wake failed: %s", err)
            await self._async_stop_client_safely()
            return False

    async def _async_stop_client_safely(self) -> None:
        """Stop the protocol client without surfacing expected transport races."""
        try:
            await self.client.stop()
        except (
            RuntimeError,
            TimeoutError,
            envy_exceptions.NotConnectedError,
            envy_exceptions.ConnectionFailedError,
            envy_exceptions.ConnectionTimeoutError,
            OSError,
        ) as err:
            self.logger.debug("Ignoring Envy client stop race: %s", err)

    async def _async_apply_sleep_transition(
        self,
        command,
        *,
        target_state: PowerState,
        protocol_message,
    ) -> None:
        """Apply a sleep/power-off transition without surfacing expected disconnects."""
        self.client.auto_reconnect = False
        try:
            await command()
        except (
            TimeoutError,
            envy_exceptions.NotConnectedError,
            envy_exceptions.ConnectionFailedError,
            envy_exceptions.ConnectionTimeoutError,
        ) as err:
            self.logger.debug(
                "Treating %s disconnect as successful lifecycle transition: %s",
                target_state.value,
                err,
            )
        await self._async_stop_client_safely()
        self._connection_state = ConnectionState.DISCONNECTED
        self._activation_live_power_sent = False
        self.client.state.apply(protocol_message)
        self._power_state = target_state
        self._device_snapshot = self.client.device_snapshot
        self._publish()


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
