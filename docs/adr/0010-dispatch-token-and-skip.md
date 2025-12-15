# ADR-0010: Dispatch Token and Skip Flag

- Status: Accepted
- Date: 2026-01-15

## Context

Cross-repo dispatch requires a token with `actions: write` and `contents: read` on target repos. Fixtures and some repos should remain central-only to avoid dispatch failures and token requirements. Artifact collisions occurred when multiple dispatch jobs used the same names.

## Decision

- Add `repo.dispatch_enabled` (default true) to config schema; orchestrator skips dispatch when false (used for fixtures/central-only repos).
- Allow orchestration to use a PAT secret (`HUB_DISPATCH_TOKEN`) with `repo` + `workflow` scopes; fallback to GITHUB_TOKEN if unset.
- Make artifact names unique per repo (e.g., `ci-report-${{ matrix.name }}`) to avoid collisions. (implementation in progress)

## Consequences

Positive:
- Avoids dispatch attempts to central-only repos.
- Explicit token path for dispatch; clearer failure mode.
- Reduces artifact name conflicts across jobs.

Negative:
- Requires managing an extra secret for dispatch-capable repos.
- More config surface (dispatch flag) to maintain.

## Alternatives Considered

- Forcing dispatch everywhere: rejected because fixtures/central-only repos lack workflows and would fail.
- Using only GITHUB_TOKEN: rejected because it often lacks cross-repo permissions.
