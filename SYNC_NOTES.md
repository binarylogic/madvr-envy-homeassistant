# madVR Envy Sync Notes (Source of Truth Workflow)

This repository is the source of truth for the madVR Envy integration.

Upstream Home Assistant repositories are deployment targets:
- `home-assistant/core` (official integration implementation)
- `home-assistant/home-assistant.io` (official docs)

## Sync Policy

1. Build and validate features here first.
2. Port to Home Assistant Core in reviewable slices.
3. Keep user-facing compatibility in core (`madvr` domain) unless a migration is included.
4. Keep intentional differences documented; avoid undocumented drift.

## Compatibility Policy (Core Target)

When targeting `home-assistant/core`:

1. Preserve existing entity `unique_id` contracts where possible.
2. Preserve existing service behavior where possible.
3. If a rename/breaking change is required, include migration/deprecation in the same PR.
4. Prefer additive changes over breaking replacements.

## Canonical vs Core Mapping

Canonical (this repo):
- Internal model and architecture can evolve freely.
- Entity model can optimize for clarity and modern usage.

Core target (`home-assistant/core`):
- Must prioritize backward compatibility for existing users.
- May use adapter/mapping layers to preserve legacy entity identity.

## PR Strategy for Core

1. PR1: runtime/client migration and stability only.
2. PR2+: additive platforms/entities/services in small slices.
3. Final PRs: cleanup and additional telemetry after compatibility baseline is merged.
