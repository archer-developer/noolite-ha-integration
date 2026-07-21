from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NooHubApi, NooHubApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


_DEVICE_BUSY = "device_busy"
_SET_STATE_MAX_ATTEMPTS = 3
_SET_STATE_RETRY_DELAY = 0.3  # seconds, multiplied by attempt number


class NooHubCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: NooHubApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self._set_state_lock = asyncio.Lock()

    async def async_set_state(self, device_id: str, state: dict) -> bool:
        """Send set_state to the hub, serialized and with device_busy retry."""
        async with self._set_state_lock:
            last_err: NooHubApiError | None = None
            for attempt in range(_SET_STATE_MAX_ATTEMPTS):
                try:
                    return await self.hass.async_add_executor_job(
                        self.api.set_state, device_id, state
                    )
                except NooHubApiError as err:
                    if err.api_message != _DEVICE_BUSY:
                        raise
                    last_err = err
                    if attempt < _SET_STATE_MAX_ATTEMPTS - 1:
                        await asyncio.sleep(_SET_STATE_RETRY_DELAY * (attempt + 1))
            _LOGGER.warning(
                "Device %s still busy after %d attempts, giving up: %s",
                device_id,
                _SET_STATE_MAX_ATTEMPTS,
                last_err,
            )
            assert last_err is not None
            raise last_err

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
