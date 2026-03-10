"""Test platform setup helpers and utility branches."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.madvr_envy import binary_sensor, button, remote, select, sensor, switch
from custom_components.madvr_envy.binary_sensor import BINARY_SENSORS, MadvrEnvyBinarySensor
from custom_components.madvr_envy.coordinator import MadvrEnvyCoordinator
from custom_components.madvr_envy.entity import MadvrEnvyEntity
from custom_components.madvr_envy.models import MadvrEnvyRuntimeState


async def test_platform_setup_entity_counts(hass, mock_envy_client):
    """Test platform setup entity creation and advanced filtering."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    basic_entry = SimpleNamespace(
        runtime_data=SimpleNamespace(coordinator=coordinator),
        options={"enable_advanced_entities": False},
    )
    full_entry = SimpleNamespace(
        runtime_data=SimpleNamespace(coordinator=coordinator),
        options={"enable_advanced_entities": True},
    )

    added_basic: list[object] = []
    added_full: list[object] = []

    await sensor.async_setup_entry(hass, basic_entry, added_basic.extend)
    await sensor.async_setup_entry(hass, full_entry, added_full.extend)
    assert len(added_basic) == len(sensor.SENSORS) - 2
    assert len(added_full) == len(sensor.SENSORS)

    added_buttons_basic: list[object] = []
    added_buttons_full: list[object] = []
    await button.async_setup_entry(hass, basic_entry, added_buttons_basic.extend)
    await button.async_setup_entry(hass, full_entry, added_buttons_full.extend)
    assert len(added_buttons_basic) < len(added_buttons_full)

    added_binary: list[object] = []
    await binary_sensor.async_setup_entry(hass, full_entry, added_binary.extend)
    assert len(added_binary) == 1

    added_switch: list[object] = []
    await switch.async_setup_entry(hass, full_entry, added_switch.extend)
    assert len(added_switch) == 1

    added_select: list[object] = []
    await select.async_setup_entry(hass, full_entry, added_select.extend)
    assert len(added_select) >= 2

    added_remote: list[object] = []
    await remote.async_setup_entry(hass, full_entry, added_remote.extend)
    assert len(added_remote) == 1

    await coordinator.async_shutdown()


def test_temperature_value_helper_branches():
    """Test temperature helper fallback behavior."""
    assert sensor._temperature_value(MadvrEnvyRuntimeState(), 0) is None
    assert sensor._temperature_value(MadvrEnvyRuntimeState(temperatures=(1, 2, 3, 4)), 9) is None
    assert sensor._nested_value(None, "resolution") is None
    assert sensor._nested_value({"aspect_ratio": "16:9"}, "aspect_ratio") == "16:9"
    assert sensor._ratio_decimal_value(None) is None
    assert sensor._ratio_decimal_value({"decimal_ratio": 2.259}) == 2.259
    assert sensor._active_profile_value(MadvrEnvyRuntimeState()) is None
    assert (
        sensor._active_profile_value(
            MadvrEnvyRuntimeState(active_profile_group="1", active_profile_index=2)
        )
        == "1: 2"
    )
    assert (
        sensor._active_profile_value(
            MadvrEnvyRuntimeState(
                active_profile_group="1",
                active_profile_index=2,
                profile_groups={"1": "Cinema"},
                profiles={"1_2": "Night"},
            )
        )
        == "Cinema: Night"
    )


def test_select_profile_id_parsing_branches():
    """Test profile id parsing edge cases."""
    assert select._parse_profile_id("1_2", None) == ("1", 2)
    assert select._parse_profile_id("2", "1") == ("1", 2)
    assert select._parse_profile_id("invalid", "1") is None
    assert select._build_profile_options({}) == []


class _DummyEntity(MadvrEnvyEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "dummy")


async def test_entity_execute_wraps_command_errors(hass, mock_envy_client):
    """Test command errors are translated to HomeAssistantError."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()

    entity = _DummyEntity(coordinator)

    async def _failing_command():
        raise TimeoutError

    with pytest.raises(HomeAssistantError):
        await entity._execute("test", _failing_command)

    await coordinator.async_shutdown()


async def test_binary_sensor_returns_unknown_during_expected_power_down(hass, mock_envy_client):
    """Test secondary binary sensors degrade to unknown during standby/off."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()
    await coordinator.async_standby()

    entity = MadvrEnvyBinarySensor(coordinator, BINARY_SENSORS[0])
    assert entity.is_on is None

    await coordinator.async_shutdown()


async def test_select_setup_restores_profile_groups_from_entity_registry(hass, mock_envy_client):
    """Test offline startup restores profile-group entities from the registry."""
    coordinator = MadvrEnvyCoordinator(hass, mock_envy_client, entry_id="test-entry")
    await coordinator.async_start()
    coordinator._profile_groups = {}
    coordinator._publish()

    entry = MockConfigEntry(
        domain="madvr_envy",
        title="madVR Envy",
        data={},
        options={"enable_advanced_entities": True},
        unique_id="madvr_envy_192.168.1.100_44077",
    )
    entry.runtime_data = SimpleNamespace(coordinator=coordinator)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "select",
        "madvr_envy",
        f"{coordinator.device_identifier}_profile_group_custom",
        config_entry=entry,
    )

    added_select: list[object] = []
    await select.async_setup_entry(hass, entry, added_select.extend)

    assert any(
        isinstance(entity, select.MadvrEnvyProfileGroupSelect) and entity._group_id == "custom"
        for entity in added_select
    )

    await coordinator.async_shutdown()
