# ADR-0035: Centralized Registry, Triage Bundle, and LLM-Ready Reports

**Status**: Implemented
**Date:** 2025-12-31
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-06

## Implementation Summary

Core features are now implemented:

**Triage System** (`.cihub/triage.json`, `priority.json`, `triage.md`, `history.jsonl`):
- Local and remote triage (`--run <id>`, `--latest`, `--watch`)
- Multi-report aggregation (`--aggregate`, `--per-repo`)
- Filtering (`--min-severity`, `--category`, `--workflow`, `--branch`)
- Historical analysis (`--gate-history`, `--detect-flaky`)
- Schema validation (`cihub hub-ci validate-triage`)

**Registry System** (`config/registry.json`):
- Tier-based config management (`strict`, `standard`, `relaxed`)
- CLI: `cihub registry list|show|set|add|diff|sync`
- Per-repo threshold overrides
- Schema: `schema/registry.schema.json`

**Fix Command** (`cihub fix`):
- Auto-fixers: `--safe` (ruff, black, isort / spotless)
- Analyzers: `--report` (all lint/security tools)
- AI output: `--ai` generates `.cihub/fix-report.md`

**Schemas**:
- `schema/triage.schema.json` with drift detection tests
- `schema/registry.schema.json` for registry validation

## Context

The hub manages multiple repositories with varying quality standards (coverage thresholds, mutation testing, vulnerability tolerance). Currently:

- Repo configs are scattered across individual `.ci-hub.yml` files
- No central view of all repo settings
- No structured output for LLM consumption (Claude, ChatGPT, Codex)
- CI failures require manual log parsing
- No priority/severity ranking for issues
- Drift between repos goes undetected

We need:
1. **Central registry** - Single JSON file with all repo configs and tiers
2. **Triage bundle** - Structured JSON + markdown output from CI runs
3. **LLM-ready format** - Standard formats (SARIF, Stryker, pytest-json) that LLMs understand
4. **Severity ranking** - Priority levels (0-10) so LLMs fix critical issues first
5. **CLI-driven sync** - Update repos from registry, not manual edits

## Decision

### 1. Centralized Registry (`config/registry.json`)

Single source of truth for all repo configurations (see `schema/registry.schema.json` for full schema):

```json
{
  "$schema": "../schema/registry.schema.json",
  "schema_version": "cihub-registry-v1",
  "tiers": {
    "strict": {
      "description": "High-quality production code with strict gates",
      "coverage": 90, "mutation": 90, "vulns_max": 0
    },
    "standard": {
      "description": "Default tier for most repos",
      "coverage": 70, "mutation": 70, "vulns_max": 0
    },
    "relaxed": {
      "description": "Legacy or experimental code with relaxed gates",
      "coverage": 50, "mutation": 0, "vulns_max": 5
    }
  },
  "repos": {
    "canary-python": {
      "tier": "standard",
      "description": "Python test fixture repo"
    },
    "canary-java": {
      "tier": "standard",
      "description": "Java test fixture repo",
      "overrides": {"mutation": 50}
    }
  }
}
```

### 2. Triage Bundle (`.cihub/triage.json`)

Structured output from every CI run (see `schema/triage.schema.json` for full schema):

```json
{
  "schema_version": "cihub-triage-v1",
  "generated_at": "2025-12-31T08:00:00Z",
  "run": {
    "correlation_id": "abc123-def456",
    "repo": "jguida941/ci-cd-hub-canary-python",
    "commit_sha": "abc123",
    "branch": "main",
    "run_id": "12345678"
  },
  "summary": {
    "overall_status": "failed",
    "failure_count": 3,
    "warning_count": 2,
    "by_severity": {"blocker": 1, "high": 1, "medium": 1}
  },
  "failures": [
    {
      "gate": "gitleaks",
      "category": "secrets",
      "severity": "blocker",
      "message": "2 secrets detected",
      "details": {}
    },
    {
      "gate": "ruff",
      "category": "lint",
      "severity": "medium",
      "message": "12 lint errors",
      "details": {}
    }
  ],
  "warnings": []
}
```

### 3. Severity Mapping (Built into CLI)

| Severity | Category      | Examples                        |
|----------|---------------|---------------------------------|
| 10       | Secrets       | gitleaks, credential exposure   |
| 9        | Supply Chain  | zizmor HIGH, workflow injection |
| 8        | Security HIGH | bandit high, pip-audit critical |
| 7        | Build/Test    | pytest failures, build errors   |
| 6        | Types         | mypy errors                     |
| 5        | Coverage      | Below threshold                 |
| 4        | Mutation      | Below threshold                 |
| 3        | Lint          | ruff errors                     |
| 2        | Format        | black, isort issues             |
| 1        | Docs          | Link check, docs drift          |
| 0        | Optional      | Missing optional tools          |

### 4. Standard Report Formats

| Report Type      | Format             | Tools                                        |
|------------------|--------------------|----------------------------------------------|
| Static Analysis  | SARIF 2.1.0        | ruff, bandit, semgrep, trivy, CodeQL, zizmor |
| Mutation Testing | Stryker Schema     | mutmut (via adapter), pitest                 |
| Test Results     | pytest-json-report | pytest                                       |
| Coverage         | Cobertura XML      | pytest-cov, jacoco                           |
| Dependencies     | CycloneDX SBOM     | pip-audit, OWASP                             |

### 5. LLM Prompt Pack (`.cihub/triage.md`)

Human/LLM readable summary with artifact links (not inline logs):

```markdown
# CI Triage Report
**Repo:** jguida941/ci-cd-hub-canary-python
**Commit:** abc123 (main)
**Time:** 2025-12-31T08:00:00Z

## Summary
- Passed: 15
- Failed: 3 (2 auto-fixable, 1 needs review)
- Skipped: 2

## Critical Issues (fix first)
| Sev | Check | Status | Action |
|-----|-------|--------|--------|
| 10 | gitleaks | 2 leaks | Manual review required |
| 7 | pytest | 3 failures | See `.cihub/artifacts/pytest.json` |
| 3 | ruff | 12 issues | Auto-fix: `ruff check --fix .` |

## Auto-Fixable
```bash
ruff check --fix .
black .
isort .
```

## Artifacts
```
- `.cihub/artifacts/ruff.sarif` (SARIF)
- `.cihub/artifacts/pytest.json` (pytest-json-report)
- `.cihub/artifacts/gitleaks.json` (JSON)
```

### 6. CLI Commands

```bash
# Registry management
cihub registry list                    # Show all repos with tiers
cihub registry show <repo>             # Show repo config + effective settings
cihub registry set <repo> --tier X     # Update tier
cihub registry set <repo> --coverage X # Override threshold
cihub registry add <repo> --tier X     # Add new repo
cihub registry diff                    # Show drift vs repo configs
cihub registry sync --dry-run          # Preview sync
cihub registry sync --yes              # Apply to repo configs

# Triage - Local mode
cihub triage                           # Generate triage from local .cihub/report.json
cihub triage --output-dir ./out        # Custom output directory
cihub triage --report path/to/report.json  # Custom report path
cihub triage --json                    # JSON output only

# Triage - Filtering
cihub triage --min-severity high       # Only failures >= severity (blocker/high/medium/low)
cihub triage --category security       # Only failures in category

# Triage - Remote mode (from GitHub workflow runs)
cihub triage --run <RUN_ID>            # Analyze specific workflow run
cihub triage --latest                  # Auto-find and triage most recent failed run
cihub triage --watch                   # Watch for new failures (background daemon)
cihub triage --watch --interval 60     # Custom polling interval (default: 30s)
cihub triage --repo owner/repo         # Target different repository

# Triage - Workflow/branch filtering
cihub triage --latest --workflow hub-ci.yml   # Filter by workflow
cihub triage --latest --branch main           # Filter by branch
cihub triage --watch --workflow hub-ci.yml --branch main  # Combined filters

# Triage - Multi-report mode (for orchestrator runs)
cihub triage --run <ID> --aggregate    # Combine multiple reports into one bundle
cihub triage --run <ID> --per-repo     # Separate bundles with index file
cihub triage --multi --reports-dir ./  # Process local directory of reports

# Triage - Historical analysis
cihub triage --gate-history            # Analyze gate status changes over time
cihub triage --detect-flaky            # Identify flaky test patterns from history

# Fix command
cihub fix --safe                       # Auto-fix: ruff, black, isort / spotless
cihub fix --safe --dry-run             # Preview what would be fixed
cihub fix --report                     # Run all analyzers, report issues
cihub fix --report --json              # JSON output for tooling
cihub fix --report --ai                # Generate AI-consumable report (.cihub/fix-report.md)

# AI/LLM output modes
cihub docs stale --ai                  # AI-consumable markdown for stale doc analysis
# Note: triage.md is auto-generated as LLM prompt pack (no flag needed)

# Schema validation
cihub hub-ci validate-triage           # Validate triage.json against schema
```

### 7. Output Paths

```
.cihub/
├── triage.json           # Full structured bundle
├── triage.md             # LLM prompt pack
├── priority.json         # Sorted failures only
├── history.jsonl         # Append-only run log
└── artifacts/
    ├── ruff.sarif
    ├── bandit.json
    ├── pytest.json
    ├── mutation.json
    └── coverage.xml
```

### 8. Validation and Lifecycle

**Schema validation** ensures the triage bundle stays stable for LLMs and downstream tools:

```bash
cihub hub-ci validate-triage                   # Validate .cihub/triage.json
cihub hub-ci validate-triage --triage-file X   # Validate specific file
```

Schema files (v1):
- `schema/triage.schema.json` - Triage bundle schema
- `schema/registry.schema.json` - Registry schema

**Planned features** (not yet implemented):
- Registry versioning with rollback support
- Retention policies (`cihub triage prune --days 30`)

### 9. Aggregate Pass Rules (Planned)

Allow composite pass/fail logic over triage output:

```json
{
  "pass_rules": {
    "require": "avg_severity < 5 AND no_blockers",
    "warn": "any_severity >= 3"
  }
}
```

### 10. Post-Mortem Logging (Planned)

Capture root-cause notes alongside drift events (in `history.jsonl`):

```json
{
  "postmortem": {
    "why": "threshold raised without backfilling tests",
    "owner": "jguida941",
    "link": "docs/adr/00xx-incident.md"
  }
}
```

### 11. Continuous Reconciliation (Planned, Opt-In)

GitOps-style drift correction (not yet implemented):

**Current implementation:**
```bash
cihub registry diff                  # Show drift from tier defaults
cihub registry sync --dry-run        # Preview what would change
cihub registry sync --yes            # Apply changes
```

**Planned enhancements:**
- `--auto` mode for automated drift correction
- `--interval` for scheduled reconciliation
- Enforcement modes: warn (default), fail (strict), auto (push fixes)

### 12. RBAC (Deferred)

Prefer GitHub permissions for the MVP. Custom role enforcement can be layered later.

### 13. DORA Metrics (Deferred)

Derived from `history.jsonl` for trend tracking:

```json
{
  "dora": {
    "deploy_frequency": 3.2,
    "lead_time_hours": 1.5,
    "change_failure_rate": 0.08,
    "mttr_hours": 0.5
  }
}
```

## Alternatives Considered

1. **Store configs in each repo**: Rejected - leads to drift, no central view
2. **Database (Postgres/SQLite)**: Deferred - JSON is simpler for MVP, schema supports future DB migration
3. **Inline artifacts in triage.json**: Rejected - bloats file, LLMs work better with links
4. **Per-repo drift baselines**: Rejected - CLI compares against registry tiers, no extra config files

## Consequences

### Positive
- Single registry.json controls all repos
- LLMs get structured, prioritized data without parsing logs
- Severity ranking ensures critical issues (secrets) fixed first
- Standard formats (SARIF, Stryker) are well-documented for LLMs
- CLI-driven workflow: `cihub registry set` + `cihub registry sync`
- Changelog provides audit trail

### Negative
- New CLI commands to maintain
- Registry must stay in sync (mitigated by `cihub registry diff`)
- Tool output normalization required for non-JSON tools (mutmut, actionlint)

### Migration Path
1. Create `config/registry.json` from existing `config/repos.yml`
2. Implement `cihub registry` commands
3. Implement `cihub triage` with SARIF/JSON output
4. Add `cihub fix --safe` for auto-fixes
5. Add `cihub assist` for LLM prompt generation
6. Deprecate manual `.ci-hub.yml` edits in favor of registry sync

## References

- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Stryker Mutation Testing Schema](https://github.com/stryker-mutator/mutation-testing-elements/blob/master/packages/report-schema/src/mutation-testing-report-schema.json)
- [pytest-json-report](https://pypi.org/project/pytest-json-report/)
- [CodeRabbit + LanceDB Case Study](https://lancedb.com/blog/case-study-coderabbit/)
- [AI Secure Code Review Pipeline](https://github.com/247arjun/ai-secure-code-review)
