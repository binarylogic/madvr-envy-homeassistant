"""Services for madVR Envy integration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, SERVICE_ACTIVATE_PROFILE, SERVICE_PRESS_KEY, SERVICE_RUN_ACTION

_SERVICE_ACTIONS: dict[str, str] = {
    "standby": "standby",
    "power_off": "power_off",
    "hotplug": "hotplug",
    "restart": "restart",
    "reload_software": "reload_software",
    "tone_map_on": "tone_map_on",
    "tone_map_off": "tone_map_off",
}


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_PRESS_KEY):
        return

    async def handle_press_key(call: ServiceCall) -> None:
        key = str(call.data["key"])
        for runtime_data in _iter_runtime_data(hass):
            await runtime_data.client.key_press(key)

    async def handle_activate_profile(call: ServiceCall) -> None:
        group_id = str(call.data["group_id"])
        profile_index = int(call.data["profile_index"])
        for runtime_data in _iter_runtime_data(hass):
            await runtime_data.client.activate_profile(group_id, profile_index)

    async def handle_run_action(call: ServiceCall) -> None:
        action = str(call.data["action"])
        command_name = _SERVICE_ACTIONS[action]
        for runtime_data in _iter_runtime_data(hass):
            command = getattr(runtime_data.client, command_name)
            await command()

    hass.services.async_register(
        DOMAIN,
        SERVICE_PRESS_KEY,
        handle_press_key,
        schema=vol.Schema({vol.Required("key"): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_PROFILE,
        handle_activate_profile,
        schema=vol.Schema(
            {
                vol.Required("group_id"): str,
                vol.Required("profile_index"): vol.Coerce(int),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_ACTION,
        handle_run_action,
        schema=vol.Schema(
            {
                vol.Required("action"): vol.In(sorted(_SERVICE_ACTIONS.keys())),
            }
        ),
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload integration services."""
    for service in (SERVICE_PRESS_KEY, SERVICE_ACTIVATE_PROFILE, SERVICE_RUN_ACTION):
        hass.services.async_remove(DOMAIN, service)


def _iter_runtime_data(hass: HomeAssistant) -> Iterable[Any]:
    return hass.data.get(DOMAIN, {}).values()
