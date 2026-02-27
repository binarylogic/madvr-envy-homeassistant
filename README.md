# madVR Envy Home Assistant Integration

Home Assistant custom integration for madVR Envy video processors, powered by [`madvr-envy`](https://github.com/binarylogic/py-madvr-envy).

## Features

- Push-based coordinator architecture (`MadvrEnvyClient` -> adapter -> bridge -> HA entities/events)
- Config flow, reauth, and options flow
- Platforms: `sensor`, `binary_sensor`, `switch`, `button`, `select`
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
- Binary sensor: signal present
- Switch: tone mapping
- Select: active profile
- Buttons: standby, power off, hotplug, restart, reload software, remote menu/info

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
