# madVR Envy Home Assistant Integration

Home Assistant custom integration for madVR Envy video processors, powered by [`madvr-envy`](https://github.com/binarylogic/py-madvr-envy).

## Features

- Push-based coordinator architecture (`MadvrEnvyClient` -> adapter -> bridge -> HA entities/events)
- Config flow, reauth, and options flow
- Platforms: `sensor`, `binary_sensor`, `switch`, `button`, `select`, `remote`
- Diagnostics with sensitive data redaction
- Production-oriented test suite and CI/release automation

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Add this repository as a custom repository (`Integration` category)
3. Install **madVR Envy**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/madvr_envy` into your Home Assistant `config/custom_components/`
2. Restart Home Assistant

## Configuration

1. Go to **Settings -> Devices & Services**
2. Click **Add Integration**
3. Search for **madVR Envy**
4. Enter host and port (default `44077`)

## Exposed Entities

- Sensors: power state, temperatures, version
- Sensors (advanced): current menu, aspect ratio mode
- Binary sensor: signal present
- Switch: tone mapping
- Select: power mode, active profile, per-profile-group selects
- Buttons: power on, standby, power off, hotplug, restart, reload software, remote menu/info/ok/back
- Remote: keypress + action commands (`action:standby`, `action:restart`, etc.)

## Services

- `madvr_envy.press_key` (`key`)
- `madvr_envy.activate_profile` (`group_id`, `profile_index`)
- `madvr_envy.run_action` (`action`: `standby|power_off|hotplug|restart|reload_software|tone_map_on|tone_map_off`)

## Exposed Events

Adapter events are forwarded to HA event bus as `madvr_envy.<event_kind>`, including:

- `madvr_envy.initial`
- `madvr_envy.system_action`
- `madvr_envy.display_changed`
- `madvr_envy.settings_uploaded`
- `madvr_envy.button`
- `madvr_envy.option_inherited`

## Development

```bash
make install
make lint
make test
```

`make install` behavior:
- If `../py-madvr-envy` exists, it installs editable local library.
- Otherwise it installs `madvr-envy` from GitHub.

## Release Process

- Conventional commits on `main`
- `release-please` opens/updates release PRs automatically
- Merging release PR creates GitHub release and uploads `madvr_envy.zip`
