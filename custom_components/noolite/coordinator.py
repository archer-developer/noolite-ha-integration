from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NooHubApi, NooHubApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class NooHubCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: NooHubApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            devices: list[dict] = await self.hass.async_add_executor_job(
                self.api.get_devices
            )
        except NooHubApiError as err:
            raise UpdateFailed(f"Error fetching NooHub devices: {err}") from err

        retrievable_ids = [d["id"] for d in devices if d.get("retrievable")]
        states: dict[str, dict] = {}
        if retrievable_ids:
            try:
                states = await self.hass.async_add_executor_job(
                    self.api.get_state, retrievable_ids
                )
            except NooHubApiError as err:
                _LOGGER.warning("Failed to fetch device states: %s", err)

        return {
            "devices": {d["id"]: d for d in devices},
            "states": states,
        }
