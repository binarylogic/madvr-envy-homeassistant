"""The madVR Envy integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from madvr_envy import MadvrEnvyClient

from .const import (
    CONF_MAC_ADDRESS,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_RECONNECT_INITIAL_BACKOFF,
    DEFAULT_RECONNECT_JITTER,
    DEFAULT_RECONNECT_MAX_BACKOFF,
    DEFAULT_SYNC_TIMEOUT,
    DEFAULT_WAKE_MODE,
    DOMAIN,
    OPT_COMMAND_TIMEOUT,
    OPT_CONNECT_TIMEOUT,
    OPT_MAC_ADDRESS,
    OPT_READ_TIMEOUT,
    OPT_RECONNECT_INITIAL_BACKOFF,
    OPT_RECONNECT_JITTER,
    OPT_RECONNECT_MAX_BACKOFF,
    OPT_SYNC_TIMEOUT,
    OPT_WAKE_MODE,
    PLATFORMS,
)
from .coordinator import MadvrEnvyCoordinator
from .lifecycle import normalize_mac_address, normalize_wake_mode
from .models import MadvrEnvyRuntimeData
from .services import async_setup_services, async_unload_services

MadvrEnvyConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: MadvrEnvyConfigEntry) -> bool:
    """Set up madVR Envy from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    client = MadvrEnvyClient(
        host=host,
        port=port,
        connect_timeout=_get_float_option(entry, OPT_CONNECT_TIMEOUT, DEFAULT_CONNECT_TIMEOUT),
        command_timeout=_get_float_option(entry, OPT_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT),
        read_timeout=_get_float_option(entry, OPT_READ_TIMEOUT, DEFAULT_READ_TIMEOUT),
        reconnect_initial_backoff=_get_float_option(
            entry,
            OPT_RECONNECT_INITIAL_BACKOFF,
            DEFAULT_RECONNECT_INITIAL_BACKOFF,
        ),
        reconnect_max_backoff=_get_float_option(
            entry,
            OPT_RECONNECT_MAX_BACKOFF,
            DEFAULT_RECONNECT_MAX_BACKOFF,
        ),
        reconnect_jitter=_get_float_option(
            entry,
            OPT_RECONNECT_JITTER,
            DEFAULT_RECONNECT_JITTER,
        ),
        auto_reconnect=True,
    )
    coordinator = MadvrEnvyCoordinator(
        hass,
        client,
        entry_id=entry.entry_id,
        sync_timeout=_get_float_option(entry, OPT_SYNC_TIMEOUT, DEFAULT_SYNC_TIMEOUT),
        device_identifier=_device_identifier(entry),
        device_label=host,
        configured_mac_address=_configured_mac_address(entry),
        wake_mode=normalize_wake_mode(entry.options.get(OPT_WAKE_MODE, DEFAULT_WAKE_MODE)),
    )

    try:
        await coordinator.async_start()
    except Exception:
        await coordinator.async_shutdown()
        raise

    runtime_data = MadvrEnvyRuntimeData(client=client, coordinator=coordinator)
    entry.runtime_data = runtime_data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime_data
    await async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def _handle_hass_stop(_event: Event) -> None:
        await coordinator.async_shutdown()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _handle_hass_stop))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MadvrEnvyConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await entry.runtime_data.coordinator.async_shutdown()
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
            hass.data.pop(DOMAIN, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: MadvrEnvyConfigEntry) -> None:
    """Handle reload request."""
    await hass.config_entries.async_reload(entry.entry_id)


def _get_float_option(entry: ConfigEntry, key: str, default: float) -> float:
    value: Any = entry.options.get(key, default)
    return float(value)


def _configured_mac_address(entry: ConfigEntry) -> str | None:
    option_value = normalize_mac_address(entry.options.get(OPT_MAC_ADDRESS))
    if option_value is not None:
        return option_value
    return normalize_mac_address(entry.data.get(CONF_MAC_ADDRESS))


def _device_identifier(entry: ConfigEntry) -> str:
    """Preserve entity ids across online and offline startups."""
    mac_address = _configured_mac_address(entry)
    if mac_address is not None:
        return mac_address.replace(":", "")

    host = str(entry.data[CONF_HOST]).strip()
    port = int(entry.data[CONF_PORT])
    host_port_unique_id = f"{DOMAIN}_{host}_{port}"

    unique_id = entry.unique_id
    if unique_id:
        if unique_id == host_port_unique_id:
            return f"{host}:{port}"
        prefix = f"{DOMAIN}_"
        if unique_id.startswith(prefix):
            suffix = unique_id[len(prefix) :]
            if suffix:
                return suffix

    return f"{host}:{port}"
