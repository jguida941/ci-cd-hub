# ADR-0064: Headless Qt Pytest Defaults

**Status:** Accepted  
**Date:** 2026-01-20  

## Context

Qt GUI repos (PySide/PyQt) frequently crash or hang in headless CI. Even with
`xvfb-run`, some test subsets (notably `qprocess`-marked tests) are unstable
without a display. Relying on manual repo edits violates the CLI-first
onboarding goal.

## Decision

When Qt dependencies are detected on Linux and no display is available, the
CLI will:

- Run pytest under `xvfb-run` when available.
- Set headless Qt environment defaults (software rendering).
- Auto-skip `qprocess`-marked tests **only if** the repo declares the marker
  and the user did not provide an explicit `-m` marker expression.

Users can override this behavior by supplying their own pytest `-m` arguments
via `python.tools.pytest.args`.

## Consequences

- Headless Qt repos run more reliably out of the box.
- Behavior remains configurable and opt-out by providing `-m` explicitly.
- No workflow/YAML changes are required; logic stays in the CLI.
