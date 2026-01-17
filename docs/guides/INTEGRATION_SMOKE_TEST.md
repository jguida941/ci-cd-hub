# Integration Smoke Test Guide (Maintainers)

**Status:** reference
**Owner:** Development Team
**Source-of-truth:** manual
**Last-reviewed:** 2026-01-15

## Purpose

Validate the CLI and config pipeline end-to-end. This guide is for maintainers
verifying releases and ensuring all CLI commands remain functional.

## Prerequisites

- Local clone of `hub-release`
- Python 3.11+ with dependencies installed
- `gh` authenticated (for GitHub steps)

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[ci]" # Needed for `cihub ci` / `cihub run`
python -m pip install -e ".[wizard]" # Needed for `cihub config edit`

python -m cihub preflight --full
```

## Recommended: CLI Self-Test (No Fixtures Repo)

This path avoids external repos. The CLI generates fixtures and tests itself.

```bash
# Light smoke (detect → init → validate)
python -m cihub smoke

# Full smoke (adds `cihub ci` where toolchains exist)
python -m cihub smoke --full

# Full matrix, keep fixtures for inspection
python -m cihub smoke --all --full --keep
```

Notes:
- `--full` runs `cihub ci`; it requires toolchains (pytest, ruff, black, isort,
 and for Java: mvn/gradle/java).
- Generated fixtures are stored in a temp directory unless `--keep` is set.

## Optional: Scaffold a Single Fixture

Use this when you want a single repo to debug:

```bash
python -m cihub scaffold python-pyproject ./smoke-python
python -m cihub smoke ./smoke-python
python -m cihub smoke --full --relax ./smoke-python
```

## Optional: Fixtures Repo Validation (CI/Regression)

If you validate against the fixtures repo, it must contain these subdirs
(source of truth is `scripts/run_cli_integration.py`):

- `java-maven-pass`
- `java-maven-fail`
- `java-gradle-pass`
- `java-gradle-fail`
- `java-multi-module-pass`
- `python-pyproject-pass`
- `python-pyproject-fail`
- `python-setup-pass`
- `python-setup-fail`
- `python-src-layout-pass`
- `monorepo-pass`
- `monorepo-fail`

Quick check:

```bash
FIXTURES=/path/to/ci-cd-hub-fixtures
REQUIRED=(java-maven-pass java-maven-fail java-gradle-pass java-gradle-fail \
 java-multi-module-pass python-pyproject-pass python-pyproject-fail \
 python-setup-pass python-setup-fail python-src-layout-pass monorepo-pass monorepo-fail)

for name in "${REQUIRED[@]}"; do
 test -d "$FIXTURES/$name" || echo "Missing fixture: $name"
done
```

### Scripted Runner

```bash
python scripts/run_cli_integration.py \
 --fixtures-path /path/to/ci-cd-hub-fixtures
```

Run a subset:

```bash
python scripts/run_cli_integration.py \
 --fixtures-path /path/to/ci-cd-hub-fixtures \
 --only java-maven-pass \
 --only python-pyproject-pass
```

## Manual Single-Case Debug (Local)

Use this when a case fails or you need to exercise commands not covered by
`cihub smoke`.

### Step 1: Scaffold a Working Copy

```bash
python -m cihub scaffold java-maven ./smoke-java
```

### Step 2: Detect Language

```bash
python -m cihub detect --repo ./smoke-java
```

Expected: `java`.

### Step 3: Init + Update

```bash
python -m cihub init \
 --repo ./smoke-java \
 --language java \
 --owner fixtures \
 --name smoke-java \
 --branch main \
 --apply

python -m cihub update \
 --repo ./smoke-java \
 --language java \
 --owner fixtures \
 --name smoke-java \
 --branch main \
 --apply \
 --force
```

Expected:
- `.ci-hub.yml` and `.github/workflows/hub-ci.yml` created

### Step 4: Validate

```bash
python -m cihub validate --repo ./smoke-java
```

Expected: `Config OK`.

### Step 5: Java-Only Fixes (Maven)

```bash
python -m cihub fix-pom --repo ./smoke-java --apply
python -m cihub fix-deps --repo ./smoke-java --apply
```

Expected: plugins and dependencies added to POMs.

### Step 6: Run CI Locally

```bash
python -m cihub ci --repo ./smoke-java --output-dir ./smoke-java/.cihub
```

For Python fixtures, add `--install-deps`.

### Step 7: Python-Only Single Tool + Reports

```bash
python -m cihub scaffold python-pyproject ./smoke-python

python -m cihub init \
 --repo ./smoke-python \
 --language python \
 --owner fixtures \
 --name smoke-python \
 --branch main \
 --apply

python -m cihub run ruff --repo ./smoke-python --output-dir ./smoke-python/.cihub
python -m cihub report build --repo ./smoke-python --output-dir ./smoke-python/.cihub
python -m cihub report summary --report ./smoke-python/.cihub/report.json
python -m cihub report outputs \
 --report ./smoke-python/.cihub/report.json \
 --output ./smoke-python/.cihub/report.outputs
python -m cihub config-outputs --repo ./smoke-python
```

## Command Coverage Checklist

Every CLI command should be exercised at least once in this guide.

| Command | Covered In |
| --- | --- |
| `detect` | Manual single-case debug |
| `init` | Manual single-case debug |
| `update` | Manual single-case debug |
| `validate` | Manual single-case debug |
| `fix-pom` | Manual single-case debug (Java) |
| `fix-deps` | Manual single-case debug (Java) |
| `ci` | CLI self-test (`--full`) + manual debug |
| `run` | Manual single-case debug (Python) |
| `report build` | Manual single-case debug |
| `report summary` | Manual single-case debug |
| `report outputs` | Manual single-case debug |
| `config-outputs` | Manual single-case debug |
| `new` | Hub-side repo management |
| `config show/set/enable/disable/edit` | Hub-side repo management |
| `sync-templates` | Hub-side repo management |
| `setup-secrets` | Secrets setup |
| `setup-nvd` | Secrets setup |
| `hub-ci *` | Hub production CI helpers |
| `scaffold` | CLI self-test |
| `smoke` | CLI self-test |
| `preflight` | CLI self-test |

## Hub-Side Repo Management (Hub Repo Only)

```bash
python -m cihub new my-repo --owner jguida941 --language python --branch main --yes
python -m cihub config --repo my-repo show
python -m cihub config --repo my-repo set python.tools.pytest.min_coverage 80
python -m cihub config --repo my-repo enable ruff
python -m cihub config --repo my-repo disable bandit
python -m cihub config --repo my-repo edit
python -m cihub sync-templates --check --dry-run --no-update-tag
```

## Secrets Setup (GitHub Required)

```bash
python -m cihub setup-secrets --hub-repo jguida941/ci-cd-hub --verify
python -m cihub setup-secrets --hub-repo jguida941/ci-cd-hub --all --verify
python -m cihub setup-nvd --verify
```

## Hub Production CI Helpers

```bash
python -m cihub hub-ci validate-configs
python -m cihub hub-ci validate-profiles
python -m cihub hub-ci ruff --path .
python -m cihub hub-ci black --path .
python -m cihub hub-ci bandit --paths cihub scripts
python -m cihub hub-ci pip-audit
python -m cihub hub-ci mutmut --workdir . --output-dir .cihub/mutmut
python -m cihub hub-ci zizmor-check --sarif zizmor.sarif
python -m cihub hub-ci license-check
python -m cihub hub-ci gitleaks-summary --outcome success
python -m cihub hub-ci summary
python -m cihub hub-ci enforce
```

## What to Capture for Review

- CLI output for any failed step
- Generated `.ci-hub.yml` and `.github/workflows/hub-ci.yml`
- JSON output when using `--json`
- GitHub Actions run URL (if testing distributed mode)
