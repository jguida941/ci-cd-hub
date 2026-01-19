# ADR-0061: Auto-Set HUB_REPO/HUB_REF Repo Variables
Status: accepted
Date: 2026-01-19

## Context

Caller workflows depend on `HUB_REPO` and `HUB_REF` GitHub repo variables so the
hub wrapper can install the correct cihub version. Repos initialized with
`cihub init` or `cihub setup` were failing in CI because these variables were
not set, even though the caller templates expect them. Manual setup is easy to
miss and breaks the “CLI-first, no manual YAML fixes” rule.

## Decision

Automate `HUB_REPO` and `HUB_REF` variable setup in onboarding flows:

- `cihub setup` sets repo variables after GitHub push when `gh` is available.
- `cihub init --apply` sets repo variables by default (opt-out via
  `--no-set-hub-vars`).
- Defaults for hub repo/ref are derived from the caller templates’ `uses` line,
  with overrides via `--hub-repo`, `--hub-ref`, `CIHUB_HUB_REPO`, and
  `CIHUB_HUB_REF`.

This keeps the hub repo source in one place (templates) and avoids hardcoding
repo names in CLI logic.

## Consequences

- Onboarding becomes self-contained: repos can go green with only cihub tooling.
- `gh` CLI authentication is now required for automatic variable setup; failures
  are reported as warnings with guidance.
- CLI help and env docs include the new flags and `CIHUB_HUB_*` variables.

## Alternatives Considered

1. **Hardcode a hub repo default in templates or CLI.** Rejected: violates the
   no-hardcoding rule and conflicts with the remediation decision to rely on
   repo variables.
2. **Leave variables manual.** Rejected: causes first-run CI failures and
   contradicts the CLI-first onboarding goal.
