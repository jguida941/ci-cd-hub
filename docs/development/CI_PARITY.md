# CI Parity Map

> **Purpose:** Documents which checks run identically in local development vs CI,
> and which differ. This helps developers understand what `cihub check` validates
> versus what `hub-production-ci.yml` runs.
>
> **Last Verified:** 2026-01-05 against `hub-production-ci.yml`

---

## Categories

- **Exact**: Same tool, same flags, same behavior
- **Partial**: Same tool, different flags/scope
- **CI-only**: Only runs in CI (requires GitHub context)
- **Local-only**: Only runs locally (not in CI workflow)

---

## Exact Match

These checks produce identical results locally and in CI.

| Check | Command | Notes |
|-------|---------|-------|
| validate-configs | `cihub hub-ci validate-configs` | Same command |
| validate-profiles | `cihub hub-ci validate-profiles` | Same command |
| validate-templates | `pytest tests/test_templates.py -v --tb=short` | Same test |
| verify-matrix-keys | `cihub hub-ci verify-matrix-keys` | Same command |

---

## Partial Match

These checks use the same underlying tool but differ in flags, scope, or output format.

| Check | Local | CI | Difference |
|-------|-------|-----|------------|
| ruff lint | `ruff check .` | `cihub hub-ci ruff --path . --force-exclude --github-output` | CI adds force-exclude + GitHub output |
| ruff format | `ruff format --check .` | `ruff format --check . --force-exclude` | CI adds force-exclude |
| mypy | `mypy cihub/ scripts/` | `mypy cihub/ --ignore-missing-imports --show-error-codes` | Scope/flags differ |
| pytest | `python -m pytest tests/ --cov=cihub --cov=scripts --cov-fail-under=70` | `python -m pytest tests/ -v --cov=cihub --cov=scripts --cov-report=xml --cov-report=term-missing --cov-fail-under=<config>` | CI adds reports/verbosity + config-driven gate |
| actionlint | `actionlint` (all workflows, optional) | `cihub hub-ci actionlint --workflow .github/workflows/hub-production-ci.yml --reviewdog` | Scope/annotations differ |
| yamllint | `yamllint config/ templates/` | `yamllint -d "{extends: relaxed, rules: {line-length: disable}}" config/defaults.yaml config/repos/ templates/profiles/` | Paths/rules differ |
| bandit | `bandit -r cihub scripts -f json -q --severity-level high --confidence-level high` | `cihub hub-ci bandit --paths cihub scripts --output ... --github-summary` | CI adds --github-summary |
| pip-audit | `pip-audit -r requirements/requirements.txt -r requirements/requirements-dev.txt` | `cihub hub-ci pip-audit --requirements ... --output ... --github-summary` | CI adds --github-summary |
| gitleaks | `gitleaks detect --source . --no-git` (skip if missing) | GitHub Action with full history | No history locally |
| trivy | `trivy fs . --severity CRITICAL,HIGH --exit-code 1` (skip if missing) | FS scan + config scan + SARIF upload | CI has more scans |
| zizmor | `zizmor .github/workflows/ --min-severity high` | SARIF output via `cihub hub-ci zizmor-run` + `cihub hub-ci zizmor-check --github-summary` | CI uses SARIF + summary |
| mutmut | `cihub hub-ci mutmut --min-score 70` | `cihub hub-ci mutmut --min-score 70 --output-dir . --github-output --github-summary` | CI adds output/summary |
| license-check | `cihub hub-ci license-check` | `cihub hub-ci license-check --github-summary` | CI adds --github-summary |

---

## CI-Only (Requires GitHub Context)

These steps only run in CI because they require GitHub APIs, tokens, or environment.

| Step | Why |
|------|-----|
| SARIF upload | Requires GitHub Security API |
| Reviewdog | Requires PR context for comments |
| dependency-review | Requires GitHub dependency graph |
| OpenSSF Scorecard | Requires GitHub repo context |
| harden-runner | GitHub Action for egress monitoring |
| badge updates | Requires commit access (GITHUB_TOKEN) |
| GH Step Summary | Requires `$GITHUB_STEP_SUMMARY` |
| hub-ci summary/enforce | Requires CI result env vars |

---

## Local-Only (Not in CI)

These steps only run locally via `cihub check` and are not in the CI workflow.

| Step | Purpose | Command |
|------|---------|---------|
| docs-check | Drift detection for CLI.md/CONFIG.md | `cihub docs check` |
| docs-links | Broken link checking | `cihub docs links` (uses lychee) |
| adr-check | ADR metadata validation | `cihub adr check` |
| preflight | Environment setup checks | `cihub preflight` |
| verify-contracts | Template/workflow contract verification | `cihub verify` |
| sync-templates-check | Remote template drift check (token required) | `cihub sync-templates --check` |
| smoke | Scaffold + validate test | `cihub smoke` |

---

## Check Tier Mapping

Shows which checks run at each `cihub check` tier:

```
cihub check              # Fast (~30s)
├── preflight
├── lint (ruff)
├── format (ruff)
├── type (mypy)
├── yamllint (optional)
├── test (pytest + coverage gate)
├── actionlint (optional)
├── docs-check
└── smoke

cihub check --audit      # + ~15s
├── docs-links
├── adr-check
├── validate-configs
└── validate-profiles

cihub check --security   # + ~2min
├── bandit
├── pip-audit
├── gitleaks (optional)
└── trivy (optional)

cihub check --full       # + ~1min
├── zizmor (optional)
├── validate-templates
├── verify-contracts
├── verify-matrix-keys
├── license-check
└── sync-templates-check (requires GH_TOKEN)

cihub check --mutation   # + ~15min
└── mutmut

cihub check --all        # Everything
```

---

## Maintaining This Document

When updating `hub-production-ci.yml` or `cihub/commands/check.py`:

1. Verify the parity map is still accurate
2. Update any changed commands or flags
3. Update the "Last Verified" date at the top
4. If adding new checks, categorize them appropriately

---

*See also: [AGENTS.md](../../AGENTS.md) for CLI-first rules and scope guardrails.*
