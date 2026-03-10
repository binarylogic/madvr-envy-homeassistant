"""Push coordinator for madVR Envy integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from madvr_envy import MadvrEnvyClient
from madvr_envy import exceptions as envy_exceptions
from madvr_envy.adapter import EnvyStateAdapter
from madvr_envy.ha_bridge import HABridgeDispatcher, coordinator_payload

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

        self._adapter = EnvyStateAdapter()
        self._dispatcher = HABridgeDispatcher(event_emitter=self._emit_bus_event)

        self._adapter_callback_handle: Any | None = None
        self._client_callback_registered = False
        self._started = False
        self._bootstrap_retry_task: asyncio.Task[None] | None = None
        self._save_task: asyncio.Task[None] | None = None

        self._connection_state = ConnectionState.DISCONNECTED
        self._power_state = PowerState.UNKNOWN
        self._mac_address = normalize_mac_address(configured_mac_address)
        self._profile_groups: dict[str, str] = {}
        self._profiles: dict[str, str] = {}
        self._payload: dict[str, Any] = {}

    async def async_start(self) -> None:
        """Start client and register callbacks once."""
        if self._started:
            return

        restored = await self._store.async_load()
        self._apply_restored_state(restored)

        if self._adapter_callback_handle is None:
            self._adapter_callback_handle = self.client.register_adapter_callback(
                self._adapter,
                self._handle_adapter_update,
            )

        if not self._client_callback_registered:
            self.client.register_callback(self._handle_client_event)
            self._client_callback_registered = True

        self._started = True
        self._publish()

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

        if self._save_task is not None:
            self._save_task.cancel()
            self._save_task = None

        if self._adapter_callback_handle is not None:
            self.client.deregister_adapter_callback(self._adapter_callback_handle)
            self._adapter_callback_handle = None

        if self._client_callback_registered:
            self.client.deregister_callback(self._handle_client_event)
            self._client_callback_registered = False

        await self.client.stop()
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

    async def async_power_on(self) -> None:
        """Wake or power on the device using the configured wake path."""
        if self.can_send_live_commands:
            await self.client.power_on()
            return
        if not self.can_wake or self._mac_address is None:
            raise envy_exceptions.NotConnectedError("No wake path configured")
        await async_send_magic_packet(self._mac_address)

    async def async_standby(self) -> None:
        """Put the device into standby."""
        await self.client.standby()
        self._power_state = PowerState.STANDBY
        self._publish()

    async def async_power_off(self) -> None:
        """Turn the device fully off."""
        await self.client.power_off()
        self._power_state = PowerState.OFF
        self._publish()

    def _emit_bus_event(self, event_type: str, event_data: dict[str, object]) -> None:
        self.hass.bus.async_fire(event_type, event_data)

    def _handle_adapter_update(self, snapshot, deltas, events) -> None:  # noqa: ANN001
        update = self._dispatcher.handle_adapter_update(snapshot, deltas, events)
        self._apply_payload(update.coordinator_data)
        self._publish()

    def _handle_client_event(self, event: str, _message: object | None = None) -> None:
        if event == "disconnected":
            self._connection_state = ConnectionState.DISCONNECTED
            self._publish()
        elif event == "connected":
            self._connection_state = ConnectionState.CONNECTED
            self._publish()
            if not self.client.state.synced:
                self._schedule_bootstrap_retry()

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
        self._apply_payload(coordinator_payload(snapshot))
        self._publish()

    def _apply_restored_state(self, restored: RestoredRuntimeState) -> None:
        self._power_state = restored.power_state
        if restored.mac_address is not None:
            self._mac_address = restored.mac_address
        self._profile_groups = dict(restored.profile_groups or {})
        self._profiles = dict(restored.profiles or {})

    def _apply_payload(self, payload: Mapping[str, Any]) -> None:
        self._payload.update(dict(payload))
        self._connection_state = (
            ConnectionState.CONNECTED if self.client.state.synced else self._connection_state
        )

        power_state = _derive_power_state(payload)
        if power_state is not PowerState.UNKNOWN:
            self._power_state = power_state

        mac_address = normalize_mac_address(payload.get("mac_address"))
        if mac_address is not None:
            self._mac_address = mac_address

        profile_groups = payload.get("profile_groups")
        if isinstance(profile_groups, dict):
            self._profile_groups = {
                str(group_id): str(group_name)
                for group_id, group_name in profile_groups.items()
                if isinstance(group_id, str) and isinstance(group_name, str)
            }

        profiles = payload.get("profiles")
        if isinstance(profiles, dict):
            self._profiles = {
                str(profile_id): str(profile_name)
                for profile_id, profile_name in profiles.items()
                if isinstance(profile_id, str) and isinstance(profile_name, str)
            }

    def _publish(self) -> None:
        self.async_set_updated_data(self._build_data())
        self._schedule_save()

    def _build_data(self) -> MadvrEnvyRuntimeState:
        return MadvrEnvyRuntimeState(
            power_state=self._power_state,
            connection_state=self._connection_state,
            wake_mode=self._wake_mode,
            mac_address=self._mac_address,
            can_wake=self.can_wake,
            can_send_live_commands=self.can_send_live_commands,
            power_control_available=self.power_control_available,
            version=_string_value(self._payload.get("version")),
            current_menu=_string_value(self._payload.get("current_menu")),
            aspect_ratio_mode=_string_value(self._payload.get("aspect_ratio_mode")),
            temperatures=_temperatures_from_payload(self._payload.get("temperatures")),
            incoming_signal=_signal_from_payload(self._payload.get("incoming_signal")),
            outgoing_signal=_signal_from_payload(self._payload.get("outgoing_signal")),
            aspect_ratio=_ratio_from_payload(self._payload.get("aspect_ratio")),
            masking_ratio=_masking_ratio_from_payload(self._payload.get("masking_ratio")),
            signal_present=_bool_value(self._payload.get("signal_present")),
            active_profile_group=_string_value(self._payload.get("active_profile_group")),
            active_profile_index=_int_value(self._payload.get("active_profile_index")),
            profile_groups=dict(self._profile_groups),
            profiles=dict(self._profiles),
            tone_map_enabled=_bool_value(self._payload.get("tone_map_enabled")),
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
                    profiles=dict(self._profiles),
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

    async def _async_retry_bootstrap_until_synced(self) -> None:
        """Keep the integration loaded while the device is offline at startup."""
        try:
            while self._started and not self.client.state.synced:
                try:
                    await self.client.start()
                    await self.client.wait_synced(timeout=self._sync_timeout)
                    self._connection_state = ConnectionState.CONNECTED
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


def _derive_power_state(payload: Mapping[str, Any]) -> PowerState:
    raw = payload.get("power_state")
    if isinstance(raw, str):
        try:
            return PowerState(raw)
        except ValueError:
            return PowerState.UNKNOWN
    return PowerState.UNKNOWN


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _bool_value(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _temperatures_from_payload(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, (tuple, list)) or len(value) < 4:
        return None
    first_four = tuple(item for item in value[:4] if isinstance(item, int))
    if len(first_four) != 4:
        return None
    return first_four  # type: ignore[return-value]


def _signal_from_payload(value: object) -> dict[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    signal: dict[str, str] = {}
    for key in ("resolution", "frame_rate", "aspect_ratio", "hdr_mode"):
        field = value.get(key)
        if isinstance(field, str):
            signal[key] = field
    return signal or None


def _ratio_from_payload(value: object) -> dict[str, str | float] | None:
    if not isinstance(value, Mapping):
        return None
    ratio: dict[str, str | float] = {}
    name = value.get("name")
    if isinstance(name, str):
        ratio["name"] = name
    decimal_ratio = value.get("decimal_ratio")
    if isinstance(decimal_ratio, (int, float)):
        ratio["decimal_ratio"] = float(decimal_ratio)
    return ratio or None


def _masking_ratio_from_payload(value: object) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    decimal_ratio = value.get("decimal_ratio")
    if isinstance(decimal_ratio, (int, float)):
        return {"decimal_ratio": float(decimal_ratio)}
    return None


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
