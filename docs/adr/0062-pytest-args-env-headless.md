# ADR-0062: Configurable Pytest Args and Env
**Status:** Accepted  
**Date:** 2026-01-19  

## Context

Some repos (especially PySide/PyQt apps) need headless pytest settings to
avoid hanging on UI event loops. Today, cihub hardcodes the pytest command and
does not allow passing extra CLI flags or environment variables. This makes it
impossible to express repo-specific pytest behavior via `.ci-hub.yml`, which
breaks the CLI-first onboarding promise and forces manual test tweaks.

## Decision

Add two optional config keys under `python.tools.pytest`:

- `args`: extra pytest CLI arguments (string or list of strings)
- `env`: environment variables to inject when running pytest

These values are read by the pytest runner and are used consistently by
`cihub ci` and `cihub run pytest`. No repo-specific defaults are added; behavior
remains opt-in via config.

## Consequences

- Repos can express headless pytest settings in config without manual workflow
  edits or hardcoding in the CLI.
- The CLI remains the single source of truth; the TypeScript CLI and wizard can
  pass these values through config handoff.
- Tests can be stabilized without changing workflow YAML.

## Alternatives Considered

1. **Hardcode Qt-specific behavior in the CLI.** Rejected: not universal and
   violates the no-hardcoding rule.
2. **Require manual test changes only.** Rejected: breaks CLI-first onboarding
   and makes CI success depend on ad-hoc repo edits.
