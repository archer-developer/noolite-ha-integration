from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NooHubApiError
from .const import DOMAIN
from .coordinator import NooHubCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NooHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        NooliteSwitchEntity(coordinator, device_id)
        for device_id, device in coordinator.data["devices"].items()
        if device["type"] == "block" and device["subtype"] in ("switch", "socket")
    ]
    async_add_entities(entities)


class NooliteSwitchEntity(CoordinatorEntity[NooHubCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: NooHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"noolite_{device_id}"
        self._opt: bool | None = None

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"][self._device_id]

    @property
    def _retrievable(self) -> bool:
        return bool(self._device.get("retrievable"))

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

    @property
    def is_on(self) -> bool | None:
        if self._retrievable:
            return self.coordinator.data["states"].get(self._device_id, {}).get("on")
        return self._opt

    async def async_turn_on(self, **kwargs) -> None:
        await self._send(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send(False)

    async def _send(self, on: bool) -> None:
        try:
            await self.coordinator.async_set_state(self._device_id, {"on": on})
        except NooHubApiError as err:
            _LOGGER.error("Failed to control %s: %s", self._device_id, err)
            return

        if not self._retrievable:
            self._opt = on
            self.async_write_ha_state()
