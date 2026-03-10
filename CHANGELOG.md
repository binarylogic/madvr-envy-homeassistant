# Changelog

## [0.3.3](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.3.2...v0.3.3) (2026-03-10)


### Bug Fixes

* keep envy entities stable when offline at startup ([ad87d21](https://github.com/binarylogic/madvr-envy-homeassistant/commit/ad87d210d596dd4447d84baef8abe75e5d777551))

## [0.3.2](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.3.1...v0.3.2) (2026-03-10)


### Bug Fixes

* keep envy lifecycle entities available in standby ([a870b80](https://github.com/binarylogic/madvr-envy-homeassistant/commit/a870b803636245cdd26242783abbd23ef71c3e0b))

## [0.3.0](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.2.0...v0.3.0) (2026-02-27)


### Features

* expose signal and aspect telemetry sensors ([3fc7928](https://github.com/binarylogic/madvr-envy-homeassistant/commit/3fc79289fcbb9fc3e349a0848fad568f9f70da05))
* improve UX with remote entity, power controls, profile-group selects, and services ([4a0645d](https://github.com/binarylogic/madvr-envy-homeassistant/commit/4a0645db7180b92816bce810d3509d8611ac95be))
* initial madVR Envy Home Assistant integration ([b0865f3](https://github.com/binarylogic/madvr-envy-homeassistant/commit/b0865f3cde4f2860f263f5bf85f4445dd5babbe0))


### Bug Fixes

* make CI pass on py311 and relax hacs validation gate ([7d88e9a](https://github.com/binarylogic/madvr-envy-homeassistant/commit/7d88e9af76a51b37ea4eccf19a7fb7fd3d07b45b))
* use cross-version FlowResult import for config flow ([ed90da8](https://github.com/binarylogic/madvr-envy-homeassistant/commit/ed90da889e37a1dd7bf3268a7dca3b008ae89882))

## [0.2.0] - 2026-02-27

### Added
- UX-focused entity improvements, including `remote` platform, power mode controls, per-profile-group selects, and richer remote action buttons.
- Integration services: `press_key`, `activate_profile`, and `run_action`.
- Additional advanced sensors for current menu and aspect ratio mode.

### Changed
- Coordinator startup priming and options validation hardening.
- CI and release workflows for reliable `master` branch automation and release packaging.

## [0.1.0] - 2026-02-27

### Added
- Initial production-ready Home Assistant integration scaffold for madVR Envy.
- Config flow + reauth + options flow with connection and options validation.
- Push coordinator wired to `MadvrEnvyClient`, `EnvyStateAdapter`, and `HABridgeDispatcher`.
- Platforms: sensor, binary_sensor, switch, button, select.
- Diagnostics with sensitive data redaction.
- CI workflows for lint/test, HACS validation, and hassfest validation.
- Release automation with release-please and release asset zip packaging.
- Test suite with high coverage and deterministic mocks.
