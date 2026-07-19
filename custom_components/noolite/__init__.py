from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import NooHubApi
from .const import (
    CONF_API_BASE_PATH,
    CONF_HOST,
    CONF_LOGIN,
    CONF_PASS,
    CONF_PROTOCOL,
    DEFAULT_API_BASE_PATH,
    DEFAULT_PROTOCOL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import NooHubCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = NooHubApi(
        host=entry.data[CONF_HOST],
        login=entry.data[CONF_LOGIN],
        password=entry.data[CONF_PASS],
        protocol=entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL),
        api_base_path=entry.data.get(CONF_API_BASE_PATH, DEFAULT_API_BASE_PATH),
    )

    coordinator = NooHubCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
