from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .api import NooHubApi, NooHubApiError
from .const import (
    CONF_API_BASE_PATH,
    CONF_HOST,
    CONF_LOGIN,
    CONF_PASS,
    CONF_PROTOCOL,
    DEFAULT_API_BASE_PATH,
    DEFAULT_PROTOCOL,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_LOGIN): str,
        vol.Required(CONF_PASS): str,
        vol.Optional(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.In(
            ["http", "https"]
        ),
        vol.Optional(CONF_API_BASE_PATH, default=DEFAULT_API_BASE_PATH): str,
    }
)


async def _validate_connection(hass: HomeAssistant, data: dict) -> None:
    api = NooHubApi(
        host=data[CONF_HOST],
        login=data[CONF_LOGIN],
        password=data[CONF_PASS],
        protocol=data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL),
        api_base_path=data.get(CONF_API_BASE_PATH, DEFAULT_API_BASE_PATH),
    )
    await hass.async_add_executor_job(api.get_devices)


class NooHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate_connection(self.hass, user_input)
            except NooHubApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
