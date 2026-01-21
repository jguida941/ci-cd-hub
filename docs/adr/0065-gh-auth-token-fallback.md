# ADR-0065: GitHub Token Fallback via gh Auth
Status: accepted
Date: 2026-01-21

## Context

CLI commands that call the GitHub API (dispatch/triage/template audits) require
an auth token. In local usage, users frequently have `gh` authenticated but do
not export `GH_TOKEN` or `GITHUB_TOKEN`. Requiring manual env setup defeats the
CLI-first “just run the tool” goal for repo setup and validation.

## Decision

When no token is provided via CLI args or environment variables, the CLI will
attempt to read a token from `gh auth token`. The priority order remains:

1. Explicit `--token`
2. Custom env var via `--token-env`
3. `GH_TOKEN`
4. `GITHUB_TOKEN`
5. `HUB_DISPATCH_TOKEN`
6. `gh auth token` fallback

If `gh` is not installed or not authenticated, behavior is unchanged and the
CLI reports a missing token.

## Consequences

- Local workflows work without extra setup if `gh auth login` is already done.
- CI continues to rely on explicit tokens (GitHub Actions provides `GITHUB_TOKEN`).
- The CLI remains the single entrypoint; users never call `gh` directly.

## Alternatives Considered

1. **Require env tokens only.** Rejected: too much manual setup for local use.
2. **Add a config file for auth.** Rejected: adds state and complexity with no
   advantage over existing `gh` auth.
