from __future__ import annotations

import requests
from requests.auth import HTTPDigestAuth


class NooHubApiError(Exception):
    pass


class NooHubApi:
    def __init__(
        self,
        host: str,
        login: str,
        password: str,
        protocol: str = "http",
        api_base_path: str = "/api",
    ) -> None:
        self._url = f"{protocol}://{host}{api_base_path}"
        self._auth = HTTPDigestAuth(login, password)

    def request(self, payload: dict) -> dict:
        try:
            resp = requests.post(
                self._url,
                json=payload,
                auth=self._auth,
                timeout=10,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
        except requests.RequestException as err:
            raise NooHubApiError(str(err)) from err

        data: dict = resp.json()
        if not data.get("success"):
            raise NooHubApiError(f"NooHub error: {data.get('message', 'unknown')}")
        return data

    def get_devices(self) -> list[dict]:
        data = self.request({"action": "get_devices"})
        return data.get("devices", [])

    def get_state(self, device_ids: list[str]) -> dict[str, dict]:
        """Return {device_id: state_dict} for retrievable devices."""
        data = self.request({"action": "get_state", "devices": device_ids})
        result: dict[str, dict] = {}
        for device in data.get("devices", []):
            state = device.get("state")
            if state and state is not False:
                result[device["id"]] = state
        return result

    def set_state(self, device_id: str, state: dict) -> bool:
        data = self.request(
            {"action": "set_state", "devices": [{"id": device_id, "state": state}]}
        )
        devices = data.get("devices", [])
        return bool(devices and devices[0].get("result"))
