"""Test entity behavior for madVR Envy platforms."""

from __future__ import annotations

from custom_components.madvr_envy.binary_sensor import BINARY_SENSORS, MadvrEnvyBinarySensor
from custom_components.madvr_envy.button import BUTTONS, MadvrEnvyButton
from custom_components.madvr_envy.coordinator import MadvrEnvyCoordinator
from custom_components.madvr_envy.select import MadvrEnvyActiveProfileSelect
from custom_components.madvr_envy.sensor import SENSORS, MadvrEnvySensor
from custom_components.madvr_envy.switch import MadvrEnvyToneMapSwitch


async def test_sensor_values(hass, mock_envy_client):
    """Test sensor values are sourced from coordinator data."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client)
    await coordinator.async_start()

    power_sensor = MadvrEnvySensor(coordinator, next(item for item in SENSORS if item.key == "power_state"))
    gpu_sensor = MadvrEnvySensor(coordinator, next(item for item in SENSORS if item.key == "gpu_temperature"))

    assert power_sensor.native_value == "on"
    assert gpu_sensor.native_value == 41

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
