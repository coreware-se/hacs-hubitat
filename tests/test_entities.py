from asyncio import Future
from hubitatmaker import Device
import pytest
from typing import Awaitable, Dict, Optional
from unittest.mock import Mock, NonCallableMock, call, patch

from custom_components.hubitat.device import Hub

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry


def mock_get_reg(_: HomeAssistant) -> Awaitable[EntityRegistry]:
    MockReg = Mock(spec=EntityRegistry)
    mock_reg = MockReg()
    mock_reg.configure_mock(entities={})
    future = Future()
    future.set_result(mock_reg)
    return future


@patch("custom_components.hubitat.entities.get_hub")
@patch(
    "custom_components.hubitat.entities.entity_registry.async_get_registry",
    new=mock_get_reg,
)
@pytest.mark.asyncio
async def test_entity_migration(get_hub: Mock) -> None:
    mock_device_1 = NonCallableMock(type="switch", attributes=["state"])
    mock_device_2 = NonCallableMock(type="fan", attributes=["state"])
    MockHub = Mock(spec=Hub)
    mock_hub = MockHub()
    mock_hub.configure_mock(
        devices={"id1": mock_device_1, "id2": mock_device_2}, token="12345"
    )

    get_hub.return_value = mock_hub

    from custom_components.hubitat.switch import HubitatSwitch
    from custom_components.hubitat.entities import create_and_add_entities

    mock_hass = Mock(spec=["async_create_task"])
    MockConfigEntry = Mock(spec=ConfigEntry)
    mock_entry = MockConfigEntry()

    def _is_switch(device: Device, overrides: Optional[Dict[str, str]] = None) -> bool:
        return device.type == "switch"

    is_switch = Mock(side_effect=_is_switch)

    mock_async_add_entities = Mock()

    await create_and_add_entities(
        mock_hass,
        mock_entry,
        mock_async_add_entities,
        "switch",
        HubitatSwitch,
        is_switch,
    )


@patch("custom_components.hubitat.entities.get_hub")
@patch("custom_components.hubitat.entities.HubitatEventEmitter")
@pytest.mark.asyncio
async def test_add_event_emitters(HubitatEventEmitter: Mock, get_hub: Mock) -> None:
    mock_device_1 = NonCallableMock(type="switch", attributes=["state"])
    mock_device_2 = NonCallableMock(type="button", attributes=["state"])
    MockHub = Mock(spec=Hub)
    mock_hub = MockHub()
    mock_hub.devices = {"id1": mock_device_1, "id2": mock_device_2}
    get_hub.return_value = mock_hub

    HubitatEventEmitter.return_value.update_device_registry = Mock(
        return_value="update_registry"
    )

    from custom_components.hubitat.entities import create_and_add_event_emitters

    mock_hass = Mock(spec=["async_create_task"])
    MockConfigEntry = Mock(spec=ConfigEntry)
    mock_entry = MockConfigEntry()

    def mock_is_emitter(device: Device) -> bool:
        return device.type == "button"

    is_emitter = Mock(side_effect=mock_is_emitter)

    await create_and_add_event_emitters(mock_hass, mock_entry, is_emitter)

    assert HubitatEventEmitter.call_count == 1, "expected 1 emitter to be created"
    assert mock_hass.async_create_task.call_count == 1, "expected 1 async creations"

    assert mock_hass.async_create_task.has_calls(
        [call("update_registry")]
    ), "1 update_device_registry task should have been created"

    assert (
        mock_hub.add_event_emitters.call_count == 1
    ), "event emitters should have been added to hub"
