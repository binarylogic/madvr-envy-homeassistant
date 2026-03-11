"""Diagnostics support for madVR Envy."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import SENSITIVE_DIAGNOSTIC_KEYS


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = entry.runtime_data.coordinator
    data = coordinator.data

    diagnostics = {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "unique_id": entry.unique_id,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "runtime": {
            "connected": coordinator.client.connected,
            "state": asdict(data) if data is not None else {},
            "host": entry.data.get(CONF_HOST),
            "port": entry.data.get(CONF_PORT),
        },
    }

    return async_redact_data(diagnostics, SENSITIVE_DIAGNOSTIC_KEYS)
