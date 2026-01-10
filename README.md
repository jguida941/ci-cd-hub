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

> [!NOTE]
> **Refactor In Progress** - We're aligning CLI/registry integration and doc automation.
> Some commands may be incomplete. See [STATUS.md](docs/development/status/STATUS.md) for current state.

---

## Why CI/CD Hub?

| Problem | Solution |
|---------|----------|
| Hours writing YAML per repo | One CLI generates config + workflows in minutes |
| Copy-paste configs that drift | 3-tier merge (defaults → hub → repo) keeps everything in sync |
| Manually configuring 10+ tools | Schema-validated config with profiles that auto-configure tools |
| Debugging cryptic CI failures | Triage bundles with prioritized, actionable reports |

---

## Who It's For

| Audience | Use Case |
|----------|----------|
| Hub/Org Admins | Centralized standards across many repos |
| Teams | Consistent CI gates across Python and Java |
| Maintainers | Minimal YAML, reproducible workflows |

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

---

## Pre-Push Validation

Run local checks before pushing:

```bash
cihub check              # Fast: lint, format, type, test (~30s)
cihub check --audit      # + links, adr, configs (~45s)
cihub check --security   # + bandit, pip-audit, trivy, gitleaks (~2min)
cihub check --full       # + templates, matrix, license, zizmor (~3min)
cihub check --all        # Everything including mutation (~15min)
```

Other validation commands:

```bash
cihub validate --repo .          # Validate .ci-hub.yml against schema
cihub run ruff --repo .          # Run one tool, emit JSON
cihub verify --remote            # Verify workflow contracts (requires gh auth)
cihub docs generate              # Regenerate CLI/config reference docs
cihub docs check                 # Verify docs are up to date
```

---

## Toolchains

### Python

| Category | Tools |
|----------|-------|
| Testing | pytest, Hypothesis |
| Linting | Ruff, Black, isort |
| Types | mypy |
| Security | Bandit, pip-audit, Semgrep, Trivy |
| Mutation | mutmut |
| Container | Docker, SBOM |

### Java

| Category | Tools |
|----------|-------|
| Testing | jqwik |
| Coverage | JaCoCo |
| Quality | Checkstyle, SpotBugs, PMD |
| Security | OWASP Dependency-Check, Semgrep, Trivy |
| Mutation | PITest |
| Container | Docker, SBOM |

### Shared (Both Languages)

Semgrep, Trivy, CodeQL, SBOM, Docker

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

Analyze CI failures:

```bash
cihub triage --latest        # Triage most recent failed run
cihub triage --run <id>      # Triage specific run by ID
```

Environment flags for debugging:

| Flag | Effect |
|------|--------|
| `CIHUB_DEBUG=True` | Show tracebacks |
| `CIHUB_VERBOSE=True` | Show tool logs |
| `CIHUB_DEBUG_CONTEXT=True` | Show decision/context blocks |
| `CIHUB_EMIT_TRIAGE=True` | Write triage bundle to `.cihub/` |

Triage outputs: `.cihub/triage.json`, `priority.json`, `triage.md`

## Installation (local development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/requirements-dev.txt
```

## Documentation

| Doc | Description |
|-----|-------------|
| [Docs Index](docs/README.md) | Full map of guides, references, and development docs |
| [Getting Started](docs/guides/GETTING_STARTED.md) | Primary entry point for new users |
| [CLI Reference](docs/reference/CLI.md) | Generated from `cihub docs generate` |
| [Config Reference](docs/reference/CONFIG.md) | Generated from schema |
| [Tools Reference](docs/reference/TOOLS.md) | Tool registry and options |
| [Troubleshooting](docs/guides/TROUBLESHOOTING.md) | Common issues and fixes |
| [Development Guide](docs/development/DEVELOPMENT.md) | Maintainer workflow |
| [Current Status](docs/development/status/STATUS.md) | Refactor progress |

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](.github/SECURITY.md).

## License

Elastic License 2.0. See [LICENSE](LICENSE).
