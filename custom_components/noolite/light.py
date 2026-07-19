from __future__ import annotations

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
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
        NooliteLightEntity(coordinator, device_id)
        for device_id, device in coordinator.data["devices"].items()
        if device["type"] == "block" and device["subtype"] == "light"
    ]
    async_add_entities(entities)


class NooliteLightEntity(CoordinatorEntity[NooHubCoordinator], LightEntity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: NooHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"noolite_{device_id}"
        # Optimistic state for Noolite TX devices (retrievable=false)
        self._opt: dict = {}

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"][self._device_id]

    @property
    def _skills(self) -> list[str]:
        return self._device.get("skills", [])

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
    def color_mode(self) -> ColorMode:
        if "color" in self._skills:
            return ColorMode.RGB
        if "brightness" in self._skills:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        return {self.color_mode}

    @property
    def _state(self) -> dict:
        if self._retrievable:
            return self.coordinator.data["states"].get(self._device_id, {})
        return self._opt

    @property
    def is_on(self) -> bool | None:
        return self._state.get("on")

    @property
    def brightness(self) -> int | None:
        pct = self._state.get("brightness")
        if pct is None:
            return None
        return round(pct * 255 / 100)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        color = self._state.get("color")
        if color is None:
            return None
        if isinstance(color, str):
            color = int(color.lstrip("#"), 16)
        return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)

    async def async_turn_on(self, **kwargs) -> None:
        state: dict = {"on": True}

        if ATTR_BRIGHTNESS in kwargs and "brightness" in self._skills:
            state["brightness"] = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)

        if ATTR_RGB_COLOR in kwargs and "color" in self._skills:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            state["color"] = (r << 16) | (g << 8) | b

        await self._send(state)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send({"on": False})

    async def _send(self, state: dict) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_state, self._device_id, state
            )
        except NooHubApiError as err:
            _LOGGER.error("Failed to control %s: %s", self._device_id, err)
            return

        if not self._retrievable:
            self._opt = {**self._opt, **state}
            self.async_write_ha_state()
