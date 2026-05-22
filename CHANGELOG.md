# Changelog

## [2.0.4](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v2.0.3...v2.0.4) (2026-05-22)


### Bug Fixes

* make Envy wake activation idempotent ([9b4c499](https://github.com/binarylogic/madvr-envy-homeassistant/commit/9b4c499387ce7b4b47baad176bd3c3345550f9a7))

## [2.0.3](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v2.0.2...v2.0.3) (2026-05-21)


### Bug Fixes

* refresh geometry after display changes ([53b47ee](https://github.com/binarylogic/madvr-envy-homeassistant/commit/53b47ee26f3903b518c7a6c69520381c0abefc71))
* retry Envy activation until on ([eb5ee92](https://github.com/binarylogic/madvr-envy-homeassistant/commit/eb5ee92f5769053a10cbc2235a2a104df8211c2c))
* wake Envy before full protocol sync ([6aeab84](https://github.com/binarylogic/madvr-envy-homeassistant/commit/6aeab84f3cc58ddd2b2ef881c11bd7d25319052c))

## [2.0.2](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v2.0.1...v2.0.2) (2026-05-17)


### Bug Fixes

* actively wake and resync Envy ([680ed34](https://github.com/binarylogic/madvr-envy-homeassistant/commit/680ed3412448deb8a6d3513cb7b6c9e8ae52a698))

## [2.0.1](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v2.0.0...v2.0.1) (2026-05-16)


### Bug Fixes

* hide unavailable madVR controls ([009d6a6](https://github.com/binarylogic/madvr-envy-homeassistant/commit/009d6a6c116b0bd86922d1939716d29d6ba5a5d4))

## [2.0.0](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v1.0.0...v2.0.0) (2026-05-16)


### ⚠ BREAKING CHANGES

* require typed madVR profile catalog

### Features

* require typed madVR profile catalog ([a323bf4](https://github.com/binarylogic/madvr-envy-homeassistant/commit/a323bf47ed23c84c9b316f844f1377e89163a627))

## [1.0.0](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.4.6...v1.0.0) (2026-05-16)


### ⚠ BREAKING CHANGES

* require madvr-envy 1.0.0 and remove HA-side protocol payload shaping in favor of typed device snapshots.

### Features

* consume typed madVR device snapshots ([aa0c0e0](https://github.com/binarylogic/madvr-envy-homeassistant/commit/aa0c0e06650a7665ea6c295ccc629118b76cc5d5))

## [0.4.6](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.4.5...v0.4.6) (2026-04-12)


### Bug Fixes

* make Envy activation use explicit ensure-on wake path ([f8b1996](https://github.com/binarylogic/madvr-envy-homeassistant/commit/f8b1996a5a6116f7b396b98641c4679a6575a481))

## [0.4.5](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.4.4...v0.4.5) (2026-03-31)


### Bug Fixes

* require explicit mac address during setup ([18ff487](https://github.com/binarylogic/madvr-envy-homeassistant/commit/18ff487146e2b04cdba10d7abf111f6d303eefdc))

## [0.4.4](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.4.3...v0.4.4) (2026-03-21)


### Bug Fixes

* restore explicit wake mac handling ([1131d1e](https://github.com/binarylogic/madvr-envy-homeassistant/commit/1131d1eaf8e303b8b74ad4cc20cc29435afae67b))

## [0.4.3](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.4.2...v0.4.3) (2026-03-11)


### Bug Fixes

* keep standby state truthful while disconnected ([3eb6356](https://github.com/binarylogic/madvr-envy-homeassistant/commit/3eb6356a58da810bb4b918ac9d2b33754daaa45f))

## [0.4.2](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.4.1...v0.4.2) (2026-03-10)


### Bug Fixes

* require madvr-envy 0.2.1 ([#15](https://github.com/binarylogic/madvr-envy-homeassistant/issues/15)) ([5478161](https://github.com/binarylogic/madvr-envy-homeassistant/commit/54781610222a010243c80d3cebf1a673630947cd))

## [0.4.1](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.4.0...v0.4.1) (2026-03-10)


### Bug Fixes

* split wake and live power control capabilities ([#13](https://github.com/binarylogic/madvr-envy-homeassistant/issues/13)) ([a2d2296](https://github.com/binarylogic/madvr-envy-homeassistant/commit/a2d2296a6839bc14b0e2c833cc37111150269131))

## [0.4.0](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.3.4...v0.4.0) (2026-03-10)


### Features

* rebuild envy lifecycle and wake handling ([#11](https://github.com/binarylogic/madvr-envy-homeassistant/issues/11)) ([2d1b57d](https://github.com/binarylogic/madvr-envy-homeassistant/commit/2d1b57dc09d27b89791cb6db7f77186e67e3dca7))

## [0.3.4](https://github.com/binarylogic/madvr-envy-homeassistant/compare/v0.3.3...v0.3.4) (2026-03-10)


### Bug Fixes

* stabilize lifecycle entities across envy sleep ([fd771d8](https://github.com/binarylogic/madvr-envy-homeassistant/commit/fd771d8b621394ae466596cfd306be370c58d69b))

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
