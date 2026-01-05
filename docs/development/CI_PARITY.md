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
| pytest | `pytest tests/` | `pytest --cov --cov-fail-under=70` | Coverage gate only in CI |
| actionlint | All workflows | Only `hub-production-ci.yml` + reviewdog | Scope/annotations differ |
| yamllint | `config/ templates/` | Specific paths + custom rules | Paths/rules differ |
| bandit | `bandit -r cihub scripts -f json -q --severity-level high --confidence-level high` | `cihub hub-ci bandit --paths cihub scripts --output ... --github-summary` | CI adds --github-summary |
| pip-audit | `pip-audit -r ...` | `cihub hub-ci pip-audit --requirements ... --output ... --github-summary` | CI adds --github-summary |
| gitleaks | `gitleaks detect --no-git` (skip if missing) | GitHub Action with full history | No history locally |
| trivy | `trivy fs .` | FS scan + config scan + SARIF upload | CI has more scans |
| zizmor | `zizmor .github/workflows/ --min-severity high` | SARIF output + `cihub hub-ci zizmor-check --github-summary` | CI uses SARIF + summary |
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
| smoke | Scaffold + validate test | `cihub smoke` |

---

## Check Tier Mapping

Shows which checks run at each `cihub check` tier:

```
cihub check              # Fast (~30s)
├── lint (ruff)
├── format (ruff)
├── type (mypy)
├── test (pytest)
├── actionlint
├── docs-check
└── smoke

cihub check --audit      # + ~15s
├── docs-links
├── adr-check
└── validate-configs

cihub check --security   # + ~2min
├── bandit
├── pip-audit
├── trivy
└── gitleaks

cihub check --full       # + ~1min
├── validate-templates
├── verify-matrix-keys
├── license-check
└── zizmor

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
