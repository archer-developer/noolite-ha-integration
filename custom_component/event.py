from __future__ import annotations

import logging

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NooHubCoordinator

_LOGGER = logging.getLogger(__name__)

_EVENT_TYPES = ["click"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NooHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        NooliteRemoteEventEntity(coordinator, device_id)
        for device_id, device in coordinator.data["devices"].items()
        if device["type"] == "remote"
    ]
    async_add_entities(entities)


class NooliteRemoteEventEntity(CoordinatorEntity[NooHubCoordinator], EventEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_event_types = _EVENT_TYPES

    def __init__(self, coordinator: NooHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"noolite_{device_id}"
        self._last_update: int | None = None

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"][self._device_id]

    @property
    def device_info(self) -> DeviceInfo:
        d = self._device
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=d["name"],
            manufacturer="Noolite",
            model=d.get("model"),
            suggested_area=d.get("room"),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        payload = self.coordinator.data["states"].get(self._device_id)
        if payload:
            event_type = payload.get("remote")
            last_update = payload.get("last_update")
            if (
                event_type
                and last_update
                and last_update != self._last_update
            ):
                self._last_update = last_update
                self._trigger_event(event_type, {"cmd": payload.get("cmd")})
        super()._handle_coordinator_update()
