# AGENTS.md - CI/CD Hub

## Project Overview

CI/CD Hub is a CLI tool and workflow wrapper for running CI across many repos. The CLI is the execution engine; workflows are thin wrappers.

## Source of Truth Hierarchy

1. **Code** (`cihub/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is authoritative CLI documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the config contract.
4. **Plan** (`docs/development/PLAN.md`) is the canonical execution plan.

## Documentation Rules

- Do not duplicate CLI help text in markdown. Generate reference docs from the CLI.
- Do not hand-write config field docs. Generate from schema.
- If code and docs conflict, update docs to match code.

## Verification Rules

- Use `cihub scaffold` + `cihub smoke` for local verification.
- The fixtures repo is for CI/regression, not required for local tests.

## Scope Rules

- One task at a time; finish before expanding scope.
- Verify current state before recommending deletions or refactors.
- Update ADRs before making major architectural changes.
- Archive superseded docs; do not delete.

## Key Files

- `cihub/cli.py` (CLI commands)
- `schema/ci-hub-config.schema.json` (config contract)
- `config/defaults.yaml` (defaults)
- `docs/development/PLAN.md` (active plan)
