# AGENTS.md - CI/CD Hub

## Project Overview

CI/CD Hub is a CLI tool and workflow wrapper for running CI across many repos. The CLI is the execution engine; workflows are thin wrappers.

## Source of Truth Hierarchy

1. **Code** (`cihub/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is authoritative CLI documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the config contract.
4. **Plan** (`docs/development/PLAN.md`) is the canonical execution plan.

## Commands

- Test: `make test`
- Lint: `make lint`
- Format: `make format`
- Typecheck: `make typecheck`
- Workflow lint: `make actionlint`
- Generate docs: `python -m cihub docs generate`
- Check docs drift: `python -m cihub docs check`
- Smoke test: `python -m cihub smoke --full`
- Local check (fast): `python -m cihub check`
- Local check (full): `python -m cihub check --all`

### Check Tiers

```
cihub check              # Fast: lint, format, type, test, docs (~30s)
cihub check --audit      # + links, adr, configs (~45s)
cihub check --security   # + bandit, pip-audit, trivy, gitleaks (~2min)
cihub check --full       # + templates, matrix, license, zizmor (~3min)
cihub check --mutation   # + mutmut (~15min)
cihub check --all        # Everything
```

## Testing Notes

- Run `pytest tests/` for CLI and config changes.
- After CLI or schema changes, regenerate reference docs.
- Use `cihub scaffold` + `cihub smoke` for local verification.

## Project Structure

- `cihub/` — CLI source and command handlers
- `config/` — Defaults and repo configs
- `schema/` — JSON schema for .ci-hub.yml
- `templates/` — Workflow/templates and scaffold assets
- `docs/` — Documentation hierarchy
- `tests/` — pytest suite
- `.github/workflows/` — CI workflows

## Documentation Rules

- Do not duplicate CLI help text in markdown. Generate reference docs from the CLI.
- Do not hand-write config field docs. Generate from schema.
- If code and docs conflict, update docs to match code.

## Scope Rules

### Always

- Update `docs/development/PLAN.md` checkboxes when scope changes.
- Update `docs/development/CHANGELOG.md` for user-facing changes.
- Regenerate docs after CLI or schema changes.

### Ask First

- Modifying `.github/workflows/`.
- Changing `schema/` or `config/repos/`.
- Archiving/moving docs or ADRs.
- Changing CLI command surface or defaults.

### Never

- Delete docs (archive instead).
- Commit secrets or credentials.
- Change workflow pins without explicit approval.

### CI Parity Rule

- If `hub-production-ci.yml` fails on something that can be reproduced locally, add it to `cihub check` or document why it's CI-only.
- Run `cihub check --all` before pushing to catch issues early.
- CI-only exceptions (cannot run locally): SARIF upload, reviewdog, dependency-review, OpenSSF Scorecard, harden-runner, badge updates, GH Step Summary.

## Key Architecture

- Entry point workflow is `hub-ci.yml` (wrapper that routes to language-specific workflows).
- Fixtures repo is CI/regression only; local dev uses `cihub scaffold` + `cihub smoke`.
- Generated refs: `docs/reference/CLI.md` and `docs/reference/CONFIG.md` (don't edit by hand).

## Key Files

- `cihub/cli.py` (CLI commands)
- `schema/ci-hub-config.schema.json` (config contract)
- `config/defaults.yaml` (defaults)
- `docs/development/PLAN.md` (active plan)
