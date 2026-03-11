"""Test entity behavior for madVR Envy platforms."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from custom_components.madvr_envy.binary_sensor import BINARY_SENSORS, MadvrEnvyBinarySensor
from custom_components.madvr_envy.button import BUTTONS, MadvrEnvyButton
from custom_components.madvr_envy.coordinator import MadvrEnvyCoordinator
from custom_components.madvr_envy.lifecycle import PowerState, WakeMode
from custom_components.madvr_envy.remote import MadvrEnvyRemote
from custom_components.madvr_envy.select import (
    MadvrEnvyActiveProfileSelect,
    MadvrEnvyPowerModeSelect,
    MadvrEnvyProfileGroupSelect,
)
from custom_components.madvr_envy.sensor import SENSORS, MadvrEnvySensor
from custom_components.madvr_envy.switch import MadvrEnvyToneMapSwitch


async def test_sensor_values(hass, mock_envy_client):
    """Test sensor values are sourced from coordinator data."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    power_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "power_state")
    )
    gpu_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "gpu_temperature")
    )
    incoming_aspect_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "incoming_signal_aspect_ratio")
    )
    masking_ratio_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "masking_ratio_decimal")
    )

    assert power_sensor.native_value == "on"
    assert gpu_sensor.native_value == 41
    assert incoming_aspect_sensor.native_value == "16:9"
    assert masking_ratio_sensor.native_value == 2.259

    await coordinator.async_shutdown()


async def test_binary_sensor_value(hass, mock_envy_client):
    """Test binary sensor state."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    entity = MadvrEnvyBinarySensor(coordinator, BINARY_SENSORS[0])
    assert entity.is_on is True

    await coordinator.async_shutdown()


async def test_tone_map_switch_calls_client(hass, mock_envy_client):
    """Test tone map switch command execution."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    entity = MadvrEnvyToneMapSwitch(coordinator)
    assert entity.available is True
    assert entity.is_on is True

    await entity.async_turn_off()
    await entity.async_turn_on()

    mock_envy_client.tone_map_off.assert_awaited_once()
    mock_envy_client.tone_map_on.assert_awaited_once()

    await coordinator.async_shutdown()


async def test_button_calls_client(hass, mock_envy_client):
    """Test button actions call client methods."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    restart_desc = next(item for item in BUTTONS if item.key == "restart")
    entity = MadvrEnvyButton(coordinator, restart_desc)
    await entity.async_press()

    mock_envy_client.restart.assert_awaited_once()

    await coordinator.async_shutdown()


async def test_profile_select_options_and_command(hass, mock_envy_client):
    """Test profile select renders options and sends activate command."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    entity = MadvrEnvyActiveProfileSelect(coordinator)

    assert "Cinema: Day" in entity.options
    assert "Cinema: Night" in entity.options
    assert entity.current_option == "Cinema: Night"

    await entity.async_select_option("Cinema: Day")
    mock_envy_client.activate_profile.assert_awaited_once_with("1", 1)

    await coordinator.async_shutdown()


async def test_power_mode_select_calls_expected_commands(hass, mock_envy_client):
    """Test power mode select dispatches power commands."""
    coordinator = MadvrEnvyCoordinator(
        hass,
        mock_envy_client,
        entry_id="test-entry",
        configured_mac_address="00:11:22:33:44:55",
    )
    await coordinator.async_start()

    entity = MadvrEnvyPowerModeSelect(coordinator)
    assert entity.current_option == "on"

    await entity.async_select_option("standby")
    await entity.async_select_option("off")
    with patch("custom_components.madvr_envy.coordinator.async_send_magic_packet", AsyncMock()) as send_wol:
        await entity.async_select_option("on")
        send_wol.assert_awaited_once_with("00:11:22:33:44:55")

    mock_envy_client.standby.assert_awaited_once()
    mock_envy_client.power_off.assert_awaited_once()
    mock_envy_client.power_on.assert_not_awaited()

    await coordinator.async_shutdown()


async def test_power_sensor_stays_explicit_through_disconnect(hass, mock_envy_client):
    """Test the lifecycle sensor stays explicit through standby/off disconnects."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    await coordinator.async_standby()
    mock_envy_client._test_callbacks["client"]("disconnected", None)

    power_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "power_state")
    )
    gpu_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "gpu_temperature")
    )
    assert power_sensor.native_value == "standby"
    assert gpu_sensor.native_value is None

    await coordinator.async_shutdown()


async def test_power_on_uses_wol_when_disconnected(hass, mock_envy_client):
    """Test power on remains available via WOL while disconnected."""
    coordinator = MadvrEnvyCoordinator(
        hass,
        mock_envy_client,
        entry_id="test-entry",
        configured_mac_address="00:11:22:33:44:55",
        wake_mode=WakeMode.AUTO,
    )
    await coordinator.async_start()
    mock_envy_client._test_callbacks["client"]("disconnected", None)

    power_desc = next(item for item in BUTTONS if item.key == "power_on")
    entity = MadvrEnvyButton(coordinator, power_desc)
    assert entity.available is True

    with patch("custom_components.madvr_envy.coordinator.async_send_magic_packet", AsyncMock()) as send_wol:
        await entity.async_press()
        send_wol.assert_awaited_once_with("00:11:22:33:44:55")

    await coordinator.async_shutdown()


async def test_only_power_on_remains_available_with_wol_when_disconnected(hass, mock_envy_client):
    """Test WOL-only sleep exposes wake but not live power-down or remote controls."""
    coordinator = MadvrEnvyCoordinator(
        hass,
        mock_envy_client,
        entry_id="test-entry",
        configured_mac_address="00:11:22:33:44:55",
        wake_mode=WakeMode.AUTO,
    )
    await coordinator.async_start()
    mock_envy_client._test_callbacks["client"]("disconnected", None)

    power_on = MadvrEnvyButton(coordinator, next(item for item in BUTTONS if item.key == "power_on"))
    standby = MadvrEnvyButton(coordinator, next(item for item in BUTTONS if item.key == "standby"))
    power_off = MadvrEnvyButton(coordinator, next(item for item in BUTTONS if item.key == "power_off"))
    remote_entity = MadvrEnvyRemote(coordinator)

    assert power_on.available is True
    assert standby.available is False
    assert power_off.available is False
    assert remote_entity.available is False

    await coordinator.async_shutdown()


async def test_power_mode_select_reflects_restored_standby(hass, mock_envy_client):
    """Test power controls stay explicit when the Envy is asleep."""
    mock_envy_client.wait_synced.side_effect = TimeoutError
    mock_envy_client.state._seen_welcome = False
    mock_envy_client.state.is_on = None
    mock_envy_client.state.standby = None
    coordinator = MadvrEnvyCoordinator(
        hass,
        mock_envy_client,
        entry_id="test-entry",
        configured_mac_address="00:11:22:33:44:55",
    )
    await coordinator.async_start()
    coordinator._power_state = PowerState.STANDBY
    coordinator._publish()
    mock_envy_client._test_callbacks["client"]("disconnected", None)

    power_mode = MadvrEnvyPowerModeSelect(coordinator)

    assert power_mode.available is True
    assert power_mode.current_option == "standby"

    await coordinator.async_shutdown()


async def test_power_mode_select_only_wakes_when_disconnected(hass, mock_envy_client):
    """Test disconnected WOL state exposes current power mode but only supports wake."""
    coordinator = MadvrEnvyCoordinator(
        hass,
        mock_envy_client,
        entry_id="test-entry",
        configured_mac_address="00:11:22:33:44:55",
        wake_mode=WakeMode.AUTO,
    )
    await coordinator.async_start()
    await coordinator.async_standby()
    mock_envy_client._test_callbacks["client"]("disconnected", None)

    power_mode = MadvrEnvyPowerModeSelect(coordinator)

    assert power_mode.available is True
    assert power_mode.current_option == "standby"

    with patch("custom_components.madvr_envy.coordinator.async_send_magic_packet", AsyncMock()) as send_wol:
        await power_mode.async_select_option("on")
        send_wol.assert_awaited_once_with("00:11:22:33:44:55")

    await coordinator.async_shutdown()


async def test_profile_group_select(hass, mock_envy_client):
    """Test profile-group scoped select entity behavior."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    entity = MadvrEnvyProfileGroupSelect(coordinator, "1")
    assert "Cinema: Day" in entity.options
    assert entity.current_option == "Cinema: Night"

    await entity.async_select_option("Cinema: Day")
    mock_envy_client.activate_profile.assert_awaited_with("1", 1)

    await coordinator.async_shutdown()


async def test_remote_send_command_and_actions(hass, mock_envy_client):
    """Test remote entity key and action command dispatch."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    entity = MadvrEnvyRemote(coordinator)
    assert entity.is_on is True
    await entity.async_turn_on()
    await entity.async_turn_off()
    await entity.async_send_command(["MENU", "action:restart", "INFO"])
    await entity.async_send_command(["", 123, "action:unknown"])  # type: ignore[list-item]

    mock_envy_client.power_on.assert_awaited_once()
    mock_envy_client.key_press.assert_any_await("MENU")
    mock_envy_client.key_press.assert_any_await("INFO")
    mock_envy_client.standby.assert_awaited()
    mock_envy_client.restart.assert_awaited_once()

    await coordinator.async_shutdown()


async def test_profile_group_select_name_fallback(hass, mock_envy_client):
    """Test profile-group select naming fallback behavior."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()
    coordinator._profile_groups = {}
    coordinator._publish()
    entity = MadvrEnvyProfileGroupSelect(coordinator, "custom")
    assert entity.name == "custom Profile"
    await coordinator.async_shutdown()


async def test_active_profile_select_returns_unknown_offline(hass, mock_envy_client):
    """Test active profile stays present but unknown when asleep."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    await coordinator.async_standby()
    entity = MadvrEnvyActiveProfileSelect(coordinator)
    assert entity.available is True
    assert entity.current_option is None

    await coordinator.async_shutdown()
