# ADR-0010: Dispatch Token and Skip Flag

- Status: Accepted
- Date: 2025-12-22

## Context

Cross-repo dispatch requires a token with `actions: write` and `contents: read` on target repos. Fixtures and some repos should remain central-only to avoid dispatch failures and token requirements. Artifact collisions occurred when multiple dispatch jobs used the same names.

## Decision

- Add `repo.dispatch_enabled` (default true) to config schema; orchestrator skips dispatch when false (used for fixtures/central-only repos).
- Allow orchestration to use a PAT secret (`HUB_DISPATCH_TOKEN`) with `repo` + `workflow` scopes; fallback to GITHUB_TOKEN if unset.
- Make artifact names unique per repo (e.g., `ci-report-${{ matrix.name }}`) to avoid collisions.
- Provide CLI command `cihub setup-secrets` to configure tokens across repos.

## CLI Setup

```bash
# Set HUB_DISPATCH_TOKEN on hub repo (prompts for PAT)
cihub setup-secrets

# Also push to all connected repos
cihub setup-secrets --all

# Non-interactive with token
cihub setup-secrets --token <PAT> --all  # Not recommended (token in shell history)
```

The CLI reads connected repos from `config/repos/*.yaml` and sets the secret on each.

## Token Requirements

**Classic PAT:** `repo` + `workflow` scopes (covers all owned repos)

**Fine-grained PAT:**
- Repository access: Include hub + all connected repos
- Permissions: Actions (Read and Write), Contents (Read), Metadata (Read)

## Consequences

Positive:
- Avoids dispatch attempts to central-only repos.
- Explicit token path for dispatch; clearer failure mode.
- Reduces artifact name conflicts across jobs.
- CLI automates secret distribution across repos.

Negative:
- Requires managing an extra secret for dispatch-capable repos.
- More config surface (dispatch flag) to maintain.

## Alternatives Considered

- Forcing dispatch everywhere: rejected because fixtures/central-only repos lack workflows and would fail.
- Using only GITHUB_TOKEN: rejected because it often lacks cross-repo permissions.
