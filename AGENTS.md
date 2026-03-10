# AGENTS.md

## Purpose
`madvr-envy-homeassistant` is the Home Assistant integration for madVR Envy.

## Workflow
- Use `uv` for local commands.
- Run repo-local lint and targeted tests before pushing.
- Keep protocol and transport quirks in `py-madvr-envy` where possible.

## Lifecycle Contract
- Keep entity unique IDs stable across online and offline startups.
- Keep the config entry loaded when the device is simply offline at startup.
- `sensor.power_state` is the primary lifecycle source of truth and should expose explicit states such as `on`, `standby`, `off`, or `unknown`.
- Secondary sensors may report `unknown` while the device is powered down.
- Reserve `unavailable` for real communication/control failure, or for entities that cannot operate without transport.

## Commits
- Use conventional commits for releasable changes: `fix: ...` or `feat: ...`.

## Releases
1. Merge normal conventional commits to `master`.
2. Let `release-please` open or update the release PR.
3. Do not manually edit version files or changelogs outside the Release Please PR.
4. Do not manually create tags or GitHub releases.
5. Merge the Release Please PR to publish.
