"""Test integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from madvr_envy import exceptions as envy_exceptions
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.madvr_envy import _device_identifier
from custom_components.madvr_envy.const import (
    DOMAIN,
    SERVICE_ACTIVATE_PROFILE,
    SERVICE_PRESS_KEY,
    SERVICE_RUN_ACTION,
)


async def test_setup_and_unload_entry(hass, mock_config_entry, mock_envy_client):
    """Test setup and unload lifecycle."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch("custom_components.madvr_envy.MadvrEnvyClient", return_value=mock_envy_client),
        patch.object(
            mock_config_entry,
            "add_update_listener",
            wraps=mock_config_entry.add_update_listener,
        ) as mock_add_update_listener,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=True),
        ) as mock_forward,
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            AsyncMock(return_value=True),
        ) as mock_unload,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        runtime_data = mock_config_entry.runtime_data
        assert runtime_data.client is mock_envy_client
        assert runtime_data.coordinator.data is not None
        assert runtime_data.coordinator.data.power_state.value == "on"
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        assert hass.services.has_service(DOMAIN, SERVICE_PRESS_KEY)
        assert hass.services.has_service(DOMAIN, SERVICE_ACTIVATE_PROFILE)
        assert hass.services.has_service(DOMAIN, SERVICE_RUN_ACTION)
        mock_add_update_listener.assert_called_once()

        mock_forward.assert_awaited_once()

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        mock_unload.assert_awaited_once()
        assert DOMAIN not in hass.data
        assert not hass.services.has_service(DOMAIN, SERVICE_PRESS_KEY)
        assert not hass.services.has_service(DOMAIN, SERVICE_ACTIVATE_PROFILE)
        assert not hass.services.has_service(DOMAIN, SERVICE_RUN_ACTION)

    mock_envy_client.start.assert_called_once()
    assert mock_envy_client.stop.await_count >= 1


async def test_setup_entry_stays_loaded_on_sync_timeout(hass, mock_config_entry, mock_envy_client):
    """Test setup stays loaded and retries if initial sync times out."""
    mock_envy_client.wait_synced.side_effect = TimeoutError
    mock_envy_client.state._seen_welcome = False
    mock_envy_client.state.is_on = None
    mock_envy_client.state.standby = None
    mock_config_entry.add_to_hass(hass)

    with (
        patch("custom_components.madvr_envy.MadvrEnvyClient", return_value=mock_envy_client),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=True),
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    runtime_data = mock_config_entry.runtime_data
    assert runtime_data.coordinator.data is not None
    assert runtime_data.coordinator.data.can_send_live_commands is False
    assert DOMAIN in hass.data
    assert hass.services.has_service(DOMAIN, SERVICE_PRESS_KEY)
    assert hass.services.has_service(DOMAIN, SERVICE_ACTIVATE_PROFILE)
    assert hass.services.has_service(DOMAIN, SERVICE_RUN_ACTION)
    mock_envy_client.stop.assert_not_called()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_entry_stays_loaded_on_initial_connection_failure(
    hass, mock_config_entry, mock_envy_client
):
    """Test startup still creates entities when the Envy is offline."""
    mock_envy_client.start.side_effect = envy_exceptions.ConnectionFailedError
    mock_envy_client.state._seen_welcome = False
    mock_envy_client.state.is_on = None
    mock_envy_client.state.standby = None
    mock_config_entry.add_to_hass(hass)

    with (
        patch("custom_components.madvr_envy.MadvrEnvyClient", return_value=mock_envy_client),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=True),
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    runtime_data = mock_config_entry.runtime_data
    assert runtime_data.coordinator.data is not None
    assert runtime_data.coordinator.data.can_send_live_commands is False
    assert DOMAIN in hass.data
    mock_envy_client.stop.assert_not_called()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_entry_uses_options_for_timeouts(hass, mock_envy_client):
    """Test entry options are used to construct client."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="madVR Envy",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 44077},
        options={
            "connect_timeout": 5.0,
            "command_timeout": 4.0,
            "read_timeout": 15.0,
            "sync_timeout": 12.0,
            "reconnect_initial_backoff": 0.5,
            "reconnect_max_backoff": 8.0,
            "reconnect_jitter": 0.1,
        },
        unique_id="madvr_envy_192.168.1.100_44077",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.madvr_envy.MadvrEnvyClient", return_value=mock_envy_client
        ) as mock_client_class,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=True),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    kwargs = mock_client_class.call_args.kwargs
    assert kwargs["connect_timeout"] == 5.0
    assert kwargs["command_timeout"] == 4.0
    assert kwargs["read_timeout"] == 15.0


def test_device_identifier_uses_legacy_mac_style_ids():
    """Test entity ids stay stable when the entry unique id is mac-based."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="madVR Envy (192.168.1.100)",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 44077},
        unique_id="madvr_envy_001122334455",
    )
    assert _device_identifier(entry) == "001122334455"


def test_device_identifier_uses_legacy_host_port_style_ids():
    """Test fallback host/port entry ids preserve the old entity id format."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="madVR Envy (192.168.1.100)",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 44077},
        unique_id="madvr_envy_192.168.1.100_44077",
    )
    assert _device_identifier(entry) == "192.168.1.100:44077"
