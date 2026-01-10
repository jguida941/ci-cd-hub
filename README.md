# CI/CD Hub

[![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/jguida941/ci-cd-hub)
[![Java](https://img.shields.io/badge/java-%23ED8B00.svg?style=for-the-badge&logo=openjdk&logoColor=white)](https://github.com/jguida941/ci-cd-hub)
[![codecov](https://img.shields.io/codecov/c/github/jguida941/ci-cd-hub?style=for-the-badge&logo=codecov&logoColor=white)](https://codecov.io/gh/jguida941/ci-cd-hub)
[![mutmut](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/mutmut.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/ruff.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![bandit](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/bandit.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![pip-audit](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/pip-audit.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![zizmor](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/zizmor.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![License: Elastic 2.0](https://img.shields.io/badge/license-Elastic%202.0-blue?style=for-the-badge)](LICENSE)

Centralized CI/CD for Java and Python repos with config-driven toggles, reusable workflows, and a single hub that runs pipelines across many repositories.

## Status Notice (Refactor In Progress)

Note: We are in a major refactor of the CLI/registry integration and doc automation. Some automation commands may be incomplete or in flux while we align registry sync/diff behavior and add `cihub docs audit` + Part 13 checks (parallel workstream). For current state, see `docs/development/status/STATUS.md` and `docs/development/active/SYSTEM_INTEGRATION_PLAN.md`.

## Why CI/CD Hub

- One CLI to run consistent CI across many repos (Python + Java) with reusable workflows.
- Schema-validated config with a clear 3-tier merge (defaults → hub → repo).
- Single commands for CI runs, report aggregation, and triage artifacts.

## Who It's For

- Hub/Org admins who want centralized standards across many repos.
- Teams that need consistent CI gates across Python and Java.
- Maintainers who want minimal YAML and reproducible workflows.

## Core Concepts

- Hub repo: hosts defaults, templates, workflows, and repo configs.
- Target repo: owns `.ci-hub.yml` for per-repo overrides.
- Merge order: defaults → hub config → repo config (repo wins).

## CLI Flow (Short)

```bash
# Guided onboarding (interactive)
python -m cihub setup

# Or generate config + workflow directly
python -m cihub init --repo . --apply

# Run CI locally (uses .ci-hub.yml)
python -m cihub ci
```

## Execution Modes

- Central mode: the hub clones repos and runs pipelines directly from a single workflow.
- Distributed mode: the hub dispatches workflows to each repo via caller templates and reusable workflows.

## Toolchains

- Java: JaCoCo, Checkstyle, SpotBugs, PMD, OWASP DC, PITest, jqwik, Semgrep, Trivy, CodeQL, SBOM, Docker.
- Python: pytest, Ruff, Black, isort, Bandit, pip-audit, mypy, mutmut, Hypothesis, Semgrep, Trivy, CodeQL, SBOM, Docker.

## Quick Start

### Central mode
```bash
# Run all repos
gh workflow run hub-run-all.yml -R jguida941/ci-cd-hub

# Run by group
gh workflow run hub-run-all.yml -R jguida941/ci-cd-hub -f run_group=fixtures
```

### Distributed mode 
1) Create a PAT with `repo` + `workflow` scopes.
2) Set `HUB_DISPATCH_TOKEN` via CLI:
   ```bash
   python -m cihub setup-secrets --all
   ```
3) In each target repo:
   ```bash
   python -m cihub init --repo . --apply
   ```
4) Set `dispatch_enabled: true` in `config/repos/<repo>.yaml`.

## Prerequisites

- Python 3.10+ (3.12 used in CI)
- GitHub Actions for workflow execution
- GitHub CLI (`gh`) recommended for dispatching workflows

## Debugging & Triage

- Tracebacks: `CIHUB_DEBUG=True`
- Tool logs: `CIHUB_VERBOSE=True`
- Triage bundle: `CIHUB_EMIT_TRIAGE=True` (writes `.cihub/triage.json`, `priority.json`, `triage.md`)

## Installation (local development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/requirements-dev.txt
```

## Documentation

- [Docs Index](docs/README.md) - Full map of guides, references, and development docs
- [Getting Started](docs/guides/GETTING_STARTED.md) - Primary entry point for new users
- [CLI Reference](docs/reference/CLI.md) - Generated from `cihub docs generate`
- [Config Reference](docs/reference/CONFIG.md) - Generated from schema
- [Tools Reference](docs/reference/TOOLS.md)
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md)
- [Development Guide](docs/development/DEVELOPMENT.md) - Maintainer workflow
- [Current Status](docs/development/status/STATUS.md)

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](.github/SECURITY.md).

## License

Elastic License 2.0. See [LICENSE](LICENSE).
