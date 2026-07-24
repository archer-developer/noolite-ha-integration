# Noolite NooHub — Home Assistant Integration

Custom component integrating Noolite (noo.by) RF smart-home devices via the NooHub Wi-Fi controller into Home Assistant.

## Architecture

```
NooHub HTTP API (Digest Auth, POST /api)
        │
   NooHubApi (api.py)          — synchronous requests wrapper
        │
 NooHubCoordinator (coordinator.py)  — DataUpdateCoordinator, polls every 30s
        │
   ┌────┴────┐
light.py   switch.py           — HA platform entities (CoordinatorEntity)
```

**Data flow per poll cycle:**
1. `get_devices` → full device list with metadata (`type`, `subtype`, `skills`, `retrievable`, `room`, `model`)
2. `get_state(retrievable_ids)` → current states only for devices where `retrievable: true`
3. Coordinator stores `{"devices": {id: device}, "states": {id: state}}`

## Key Files

| File | Role |
|------|------|
| `api.py` | `NooHubApi` — all HTTP calls; raises `NooHubApiError` on failure |
| `coordinator.py` | `NooHubCoordinator` — poll logic, wraps sync API calls via `async_add_executor_job` |
| `config_flow.py` | UI setup flow; validates connection before creating entry |
| `light.py` | `NooliteLightEntity` — supports ONOFF / BRIGHTNESS / RGB based on device `skills` |
| `switch.py` | `NooliteSwitchEntity` — simple on/off |
| `const.py` | Domain constants and defaults |

## Device Model

NooHub devices relevant to this integration:

```json
{
  "id": "device-uuid",
  "name": "Bedroom Light",
  "type": "block",
  "subtype": "light",          // light | socket | switch | thermostat | curtain | sensor
  "skills": ["brightness", "color"],
  "retrievable": true,         // false = TX-only, no feedback
  "room": "Bedroom",
  "model": "SUF-1-300"
}
```

**`skills` array** controls which `ColorMode` is assigned to a light:
- `["color"]` → `ColorMode.RGB`
- `["brightness"]` → `ColorMode.BRIGHTNESS`
- `[]` → `ColorMode.ONOFF`

**`retrievable: false`** means the device is a pure RF transmitter with no state feedback. Both `light.py` and `switch.py` handle this with an optimistic local state (`_opt`) that is written immediately after a successful `set_state` call.

## API Contract

All calls are `POST /api` with JSON body and HTTP Digest Auth.

```python
# List devices
{"action": "get_devices"}
# → {"success": true, "devices": [...]}

# Get state for retrievable devices
{"action": "get_state", "devices": ["id1", "id2"]}
# → {"success": true, "devices": [{"id": "id1", "state": {"on": true, "brightness": 80}}, ...]}

# Set state
{"action": "set_state", "devices": [{"id": "id1", "state": {"on": true, "brightness": 50}}]}
# → {"success": true, "devices": [{"id": "id1", "result": true}]}
```

State dict fields: `on` (bool), `brightness` (0–100 int), `color` (int or `#RRGGBB` hex string).

## Adding a New Platform

1. Add the new HA platform type to `PLATFORMS` in `const.py`
2. Create `<platform>.py` following the pattern of `light.py` or `switch.py`:
   - Filter devices by `type`/`subtype` in `async_setup_entry`
   - Extend `CoordinatorEntity` + the HA entity base class
   - Use `coordinator.data["states"].get(id)` for retrievable, `self._opt` for TX-only
3. Add translations to `strings.json`, `translations/en.json`, `translations/ru.json` if the platform introduces new config fields

## Development Notes

- The `api.py` client uses synchronous `requests`; always wrap calls with `hass.async_add_executor_job` inside the async HA layer.
- `DEFAULT_SCAN_INTERVAL = 30` seconds — adjust in `const.py` if needed.
- Config entry title is set to the host address (`user_input[CONF_HOST]`).
- `unique_id` for entities is `noolite_{device_id}` — device IDs come from NooHub and must be stable UUIDs.
