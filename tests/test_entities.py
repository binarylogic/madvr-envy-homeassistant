"""Test entity behavior for madVR Envy platforms."""

from __future__ import annotations

from custom_components.madvr_envy.binary_sensor import BINARY_SENSORS, MadvrEnvyBinarySensor
from custom_components.madvr_envy.button import BUTTONS, MadvrEnvyButton
from custom_components.madvr_envy.coordinator import MadvrEnvyCoordinator
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
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
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
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    entity = MadvrEnvyBinarySensor(coordinator, BINARY_SENSORS[0])
    assert entity.is_on is True

    await coordinator.async_shutdown()


async def test_tone_map_switch_calls_client(hass, mock_envy_client):
    """Test tone map switch command execution."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    entity = MadvrEnvyToneMapSwitch(coordinator)
    assert entity.is_on is True

    await entity.async_turn_off()
    await entity.async_turn_on()

    mock_envy_client.tone_map_off.assert_awaited_once()
    mock_envy_client.tone_map_on.assert_awaited_once()

    await coordinator.async_shutdown()


async def test_button_calls_client(hass, mock_envy_client):
    """Test button actions call client methods."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    restart_desc = next(item for item in BUTTONS if item.key == "restart")
    entity = MadvrEnvyButton(coordinator, restart_desc)
    await entity.async_press()

    mock_envy_client.restart.assert_awaited_once()

    await coordinator.async_shutdown()


async def test_profile_select_options_and_command(hass, mock_envy_client):
    """Test profile select renders options and sends activate command."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
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
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    entity = MadvrEnvyPowerModeSelect(coordinator)
    assert entity.current_option == "on"

    await entity.async_select_option("standby")
    await entity.async_select_option("off")
    await entity.async_select_option("on")

    mock_envy_client.standby.assert_awaited_once()
    mock_envy_client.power_off.assert_awaited_once()
    mock_envy_client.key_press.assert_awaited_with("POWER")

    await coordinator.async_shutdown()


async def test_power_sensor_stays_available_during_expected_power_down(hass, mock_envy_client):
    """Test the lifecycle sensor stays explicit through standby/off disconnects."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            "available": False,
            "power_state": "standby",
            "temperatures": None,
        }
    )

    power_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "power_state")
    )
    gpu_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "gpu_temperature")
    )
    assert power_sensor.available is True
    assert power_sensor.native_value == "standby"
    assert gpu_sensor.available is True
    assert gpu_sensor.native_value is None

    await coordinator.async_shutdown()


async def test_power_mode_select_is_unavailable_when_transport_is_down(hass, mock_envy_client):
    """Test the power select stays present through expected standby/off disconnects."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            "available": False,
            "power_state": "standby",
        }
    )

    power_mode = MadvrEnvyPowerModeSelect(coordinator)

    assert power_mode.available is True
    assert power_mode.current_option == "standby"

    await coordinator.async_shutdown()


async def test_power_sensor_reports_last_known_state_on_true_disconnect(hass, mock_envy_client):
    """Test the lifecycle sensor remains explicit across disconnect timing races."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            "available": False,
            "power_state": "on",
        }
    )

    power_sensor = MadvrEnvySensor(
        coordinator, next(item for item in SENSORS if item.key == "power_state")
    )

    assert power_sensor.available is True
    assert power_sensor.native_value == "on"

    await coordinator.async_shutdown()


async def test_profile_group_select(hass, mock_envy_client):
    """Test profile-group scoped select entity behavior."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    entity = MadvrEnvyProfileGroupSelect(coordinator, "1")
    assert "Cinema: Day" in entity.options
    assert entity.current_option == "Cinema: Night"

    await entity.async_select_option("Cinema: Day")
    mock_envy_client.activate_profile.assert_awaited_with("1", 1)

    await coordinator.async_shutdown()


async def test_remote_send_command_and_actions(hass, mock_envy_client):
    """Test remote entity key and action command dispatch."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    entity = MadvrEnvyRemote(coordinator)
    assert entity.is_on is True
    await entity.async_turn_on()
    await entity.async_turn_off()
    await entity.async_send_command(["MENU", "action:restart", "INFO"])
    await entity.async_send_command(["", 123, "action:unknown"])  # type: ignore[list-item]

    mock_envy_client.key_press.assert_any_await("POWER")
    mock_envy_client.key_press.assert_any_await("MENU")
    mock_envy_client.key_press.assert_any_await("INFO")
    mock_envy_client.standby.assert_awaited()
    mock_envy_client.restart.assert_awaited_once()

    await coordinator.async_shutdown()


async def test_profile_group_select_name_fallback(hass, mock_envy_client):
    """Test profile-group select naming fallback behavior."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()
    coordinator.data["profile_groups"] = {}
    entity = MadvrEnvyProfileGroupSelect(coordinator, "custom")
    assert entity.name == "custom Profile"
    await coordinator.async_shutdown()


async def test_active_profile_select_returns_unknown_offline(hass, mock_envy_client):
    """Test active profile stays present but unknown when transport is down."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    coordinator.async_set_updated_data(
        {
            **coordinator.data,
            "available": False,
            "power_state": "standby",
            "active_profile_group": None,
            "active_profile_index": None,
        }
    )

    entity = MadvrEnvyActiveProfileSelect(coordinator)
    assert entity.available is True
    assert entity.current_option is None

    await coordinator.async_shutdown()
