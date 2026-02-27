# Changelog

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
