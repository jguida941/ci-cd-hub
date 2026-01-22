# ADR-0072: Require Verified Hub Repo Vars on Init/Setup
Status: accepted
Date: 2026-01-22

## Context

Caller workflows depend on `HUB_REPO` and `HUB_REF` repository variables to
install the correct hub version. When these variables are missing or stale, the
workflow falls back to an old ref and silently drifts from the CLI/config
contract, causing "works locally but fails in CI" behavior across repos.

## Decision

`cihub init` and `cihub setup` must verify that `HUB_REPO` and `HUB_REF` are
successfully set when `--set-hub-vars` is enabled (default). If verification
fails, the command exits with a non‑zero status and an explicit error.

This makes repo onboarding deterministic and prevents silent drift from stale
hub refs.

## Consequences

- Repo setup fails fast when hub variables cannot be set (missing gh auth,
  unknown repo, or unresolved hub ref).
- CI uses consistent hub versions across all repos pinned to `@v1`.
- Users must resolve GitHub auth/permissions during onboarding instead of after
  failed CI runs.

## Alternatives Considered

1. **Warn only and continue.** Rejected: silent drift to stale hub refs keeps
   breaking repos after "successful" setup.
2. **Hardcode fallback values.** Rejected: violates no‑hardcoding and makes
   upgrades unpredictable.
