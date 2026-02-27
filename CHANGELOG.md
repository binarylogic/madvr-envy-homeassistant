# Changelog

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
