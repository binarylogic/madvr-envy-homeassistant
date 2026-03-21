"""Config flow for madVR Envy integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from madvr_envy import MadvrEnvyClient
from madvr_envy import exceptions as envy_exceptions

from .const import (
    CONF_MAC_ADDRESS,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_ENABLE_ADVANCED_ENTITIES,
    DEFAULT_PORT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_RECONNECT_INITIAL_BACKOFF,
    DEFAULT_RECONNECT_JITTER,
    DEFAULT_RECONNECT_MAX_BACKOFF,
    DEFAULT_SYNC_TIMEOUT,
    DEFAULT_WAKE_MODE,
    DOMAIN,
    NAME,
    OPT_COMMAND_TIMEOUT,
    OPT_CONNECT_TIMEOUT,
    OPT_ENABLE_ADVANCED_ENTITIES,
    OPT_MAC_ADDRESS,
    OPT_READ_TIMEOUT,
    OPT_RECONNECT_INITIAL_BACKOFF,
    OPT_RECONNECT_JITTER,
    OPT_RECONNECT_MAX_BACKOFF,
    OPT_SYNC_TIMEOUT,
    OPT_WAKE_MODE,
)
from .lifecycle import WakeMode, normalize_mac_address, normalize_wake_mode

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_MAC_ADDRESS): str,
    }
)


class MadvrEnvyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for madVR Envy."""

    VERSION = 1
    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])

            try:
                mac_address = _normalize_manual_mac_input(user_input.get(CONF_MAC_ADDRESS))
            except ValueError:
                errors[CONF_MAC_ADDRESS] = "invalid_mac"
            else:
                unique_id, discovered_mac = await _validate_connection(host, port)
                if unique_id is None:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: host, CONF_PORT: port}
                    )
                    title = f"{NAME} ({host})"
                    data = {CONF_HOST: host, CONF_PORT: port}
                    if mac_address is None:
                        mac_address = discovered_mac
                    if mac_address is not None:
                        data[CONF_MAC_ADDRESS] = mac_address
                    return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth flow."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm(entry_data)

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])

            unique_id, mac_address = await _validate_connection(host, port)
            if unique_id is None:
                errors["base"] = "cannot_connect"
            else:
                data = {**self._reauth_entry.data, CONF_HOST: host, CONF_PORT: port}
                if mac_address is not None:
                    data[CONF_MAC_ADDRESS] = mac_address
                self.hass.config_entries.async_update_entry(self._reauth_entry, data=data)
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=self._reauth_entry.data.get(CONF_HOST, "")
                    ): str,
                    vol.Required(
                        CONF_PORT,
                        default=self._reauth_entry.data.get(CONF_PORT, DEFAULT_PORT),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MadvrEnvyOptionsFlowHandler(config_entry)


class MadvrEnvyOptionsFlowHandler(OptionsFlow):
    """Handle madVR Envy options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            initial_backoff = float(user_input[OPT_RECONNECT_INITIAL_BACKOFF])
            max_backoff = float(user_input[OPT_RECONNECT_MAX_BACKOFF])
            jitter = float(user_input[OPT_RECONNECT_JITTER])
            if initial_backoff > max_backoff:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_build_options_schema(self._config_entry),
                    errors={"base": "invalid_backoff"},
                )
            if jitter < 0.0 or jitter > 1.0:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_build_options_schema(self._config_entry),
                    errors={"base": "invalid_jitter"},
                )
            try:
                mac_address = _normalize_manual_mac_input(user_input.get(OPT_MAC_ADDRESS))
            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_build_options_schema(self._config_entry),
                    errors={OPT_MAC_ADDRESS: "invalid_mac"},
                )
            return self.async_create_entry(
                title="",
                data={
                    **user_input,
                    OPT_MAC_ADDRESS: mac_address or "",
                    OPT_WAKE_MODE: normalize_wake_mode(user_input[OPT_WAKE_MODE]).value,
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(self._config_entry),
        )


async def _validate_connection(host: str, port: int) -> tuple[str | None, str | None]:
    client = MadvrEnvyClient(host=host, port=port)
    try:
        await client.start()
        await client.wait_synced(timeout=DEFAULT_SYNC_TIMEOUT)
    except (
        envy_exceptions.ConnectionFailedError,
        envy_exceptions.ConnectionTimeoutError,
        envy_exceptions.NotConnectedError,
        TimeoutError,
    ):
        return None, None
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error during madVR Envy connection validation")
        return None, None
    finally:
        await client.stop()

    mac_address = normalize_mac_address(client.state.mac_address)
    if mac_address:
        normalized_mac = mac_address.replace(":", "")
        return f"{DOMAIN}_{normalized_mac}", mac_address

    return f"{DOMAIN}_{host}_{port}", None


def _build_options_schema(config_entry: ConfigEntry) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                OPT_SYNC_TIMEOUT,
                default=config_entry.options.get(OPT_SYNC_TIMEOUT, DEFAULT_SYNC_TIMEOUT),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
            vol.Required(
                OPT_CONNECT_TIMEOUT,
                default=config_entry.options.get(OPT_CONNECT_TIMEOUT, DEFAULT_CONNECT_TIMEOUT),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
            vol.Required(
                OPT_COMMAND_TIMEOUT,
                default=config_entry.options.get(OPT_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
            vol.Required(
                OPT_READ_TIMEOUT,
                default=config_entry.options.get(OPT_READ_TIMEOUT, DEFAULT_READ_TIMEOUT),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
            vol.Required(
                OPT_RECONNECT_INITIAL_BACKOFF,
                default=config_entry.options.get(
                    OPT_RECONNECT_INITIAL_BACKOFF,
                    DEFAULT_RECONNECT_INITIAL_BACKOFF,
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
            vol.Required(
                OPT_RECONNECT_MAX_BACKOFF,
                default=config_entry.options.get(
                    OPT_RECONNECT_MAX_BACKOFF,
                    DEFAULT_RECONNECT_MAX_BACKOFF,
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
            vol.Required(
                OPT_RECONNECT_JITTER,
                default=config_entry.options.get(
                    OPT_RECONNECT_JITTER,
                    DEFAULT_RECONNECT_JITTER,
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Required(
                OPT_WAKE_MODE,
                default=normalize_wake_mode(
                    config_entry.options.get(OPT_WAKE_MODE, DEFAULT_WAKE_MODE)
                ).value,
            ): vol.In([mode.value for mode in WakeMode]),
            vol.Required(
                OPT_MAC_ADDRESS,
                default=config_entry.options.get(
                    OPT_MAC_ADDRESS,
                    config_entry.data.get(CONF_MAC_ADDRESS, ""),
                ),
            ): str,
            vol.Required(
                OPT_ENABLE_ADVANCED_ENTITIES,
                default=config_entry.options.get(
                    OPT_ENABLE_ADVANCED_ENTITIES,
                    DEFAULT_ENABLE_ADVANCED_ENTITIES,
                ),
            ): bool,
        }
    )


def _normalize_manual_mac_input(raw_mac: object) -> str | None:
    """Normalize a manually supplied MAC address or raise when malformed."""
    if raw_mac is None:
        return None
    if not isinstance(raw_mac, str):
        raise ValueError("Invalid MAC address")

    mac = raw_mac.strip()
    if not mac:
        return None

    normalized = normalize_mac_address(mac)
    if normalized is None:
        raise ValueError("Invalid MAC address")
    return normalized
