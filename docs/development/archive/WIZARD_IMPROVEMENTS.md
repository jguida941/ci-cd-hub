# Wizard Improvements Plan

> **WARNING: SUPERSEDED:** This document has been consolidated into `docs/development/active/SYSTEM_INTEGRATION_PLAN.md` (2026-01-08)

**Status:** ARCHIVED
**Owner:** Development Team
**Last Updated:** 2026-01-08

## Executive Summary

The wizard needs several improvements to be "enterprise, not class-project":

1. **Profile-first selection** - Use existing profiles instead of individual checkboxes
2. **Fix tool run truthfulness** - Only run tools that are enabled
3. **Format mode choice** - check vs auto-format for black/isort
4. **Sane Bandit defaults** - Auto-exclude `.venv/`, summarize findings
5. **Plain English gates** - Explain what failures mean
6. **Config preview** - Show diff before writing files

## Current State Analysis

### What We Have (Good)

We already have **6 profiles per language** in `templates/profiles/`:

| Profile | Description | Runtime |
|---------|-------------|---------|
| `minimal` | Fastest sanity check | ~2-5 min |
| `fast` | Quick PR feedback | ~3-8 min |
| `quality` | Thorough analysis | ~15-30 min |
| `security` | Security scanning only | ~15-30 min |
| `compliance` | Security/compliance gates | ~15-30 min |
| `coverage-gate` | High coverage/mutation | ~12-20 min |

These profiles already include sensible settings like:
- `fail_on_format_issues: false` (black check mode)
- `fail_on_high: true` (bandit high-severity only)
- Coverage/mutation thresholds

### What's Broken

1. **Wizard doesn't surface profiles** - Goes straight to individual tool checkboxes
2. **Tool run truthfulness** - `tools_ran: true` even when `configured: false`
3. **No format mode choice** - Can't choose between check vs auto-format
4. **Bandit outputs raw findings** - No summarization or smart filtering
5. **Gates not explained** - Users see numbers, not meaning
6. **No preview** - Files written without showing what changes

## Proposed Changes

### Priority 1: Profile-First Selection (High Impact, Medium Effort)

**Before:**
```
Step 3: Configure CI Tools
 Enable pytest? [Y/n]
 Enable ruff? [Y/n]
 Enable black? [Y/n]
 ... (13 more tools)
```

**After:**
```
Step 3: Select Profile
 ○ Fast (Recommended) - pytest, ruff, black, bandit, pip-audit (~5 min)
 ○ Quality - Fast + mypy, mutmut (~20 min)
 ○ Strict - Quality + semgrep, trivy, codeql (~30 min)
 ○ Custom - Configure each tool individually
```

Then if "Custom" is selected, show the individual tool prompts.

**Implementation:**
- Modify `cihub/wizard/core.py` to add profile selection step
- Load profile from `templates/profiles/{language}-{profile}.yaml`
- Fall back to individual checkboxes if "Custom" selected

### Priority 2: Format Mode Choice (High Impact, Low Effort)

Add to profile/tool config:
```yaml
black:
 enabled: true
 mode: check # or "fix"
```

**Wizard prompt:**
```
Black formatting:
 ○ Check only - Fail CI if code not formatted
 ○ Auto-format - Fix formatting automatically (Recommended)
```

### Priority 3: Sane Bandit Defaults (High Impact, Low Effort)

Current profiles already have `fail_on_high: true`. Add:
```yaml
bandit:
 enabled: true
 fail_on_high: true
 exclude: [".venv", "tests", "build", "dist"]
 summary_only: true # Don't dump all findings, just counts
```

### Priority 4: Plain English Gates (Medium Impact, Low Effort)

After threshold configuration, show:
```
Summary of your gates:
 [x] CI will fail if coverage < 70%
 [x] CI will fail if any critical/high vulnerability is found
 [x] CI will warn (not fail) if formatting issues exist
```

### Priority 5: Config Preview (Medium Impact, Medium Effort)

Before writing files, show:
```
Files to be created:
 .ci-hub.yml (new)
 .github/workflows/hub-ci.yml (new)

Preview .ci-hub.yml:
┌──────────────────────────────────────────┐
│ language: python │
│ python: │
│ version: "3.12" │
│ tools: │
│ pytest: │
│ enabled: true │
│ min_coverage: 70 │
│ ... │
└──────────────────────────────────────────┘

Write these files? [Y/n]
```

## Design Decisions Needed

### Q1: Black Check vs Fix Mode

**Options:**
1. Default to `check` (fail CI, user fixes locally)
2. Default to `fix` (auto-format in CI, may surprise users)
3. Always ask in wizard (current approach)

**Recommendation:** Default to `check` in CI, but let `cihub fix` do auto-formatting locally.

### Q2: Tool Config Location

**Options:**
1. All config in `.ci-hub.yml` (current approach)
2. Tool-specific config in `pyproject.toml` (e.g., `[tool.black]`)
3. Hybrid - reference external configs from `.ci-hub.yml`

**Recommendation:** Keep all CI config in `.ci-hub.yml` for single source of truth. Let users manually create `pyproject.toml` sections if they want IDE integration.

### Q3: Multi-CI Support

**Options:**
1. GitHub Actions only (current)
2. Generate GitLab CI, CircleCI, etc.
3. Generic config that works everywhere

**Recommendation:** GitHub Actions as primary target. Add GitLab/other support in v2.0 if needed.

## Implementation Checklist

### Phase 1: Profile Selection (This Sprint)
- [ ] Add profile loading to wizard
- [ ] Create profile selection prompt
- [ ] Map user-friendly names ("Fast", "Quality", "Strict") to profile files
- [ ] Keep "Custom" option for individual tool selection

### Phase 2: Format Mode & Bandit (Next Sprint)
- [ ] Add `mode: check|fix` to black/isort config
- [ ] Add wizard prompt for format mode
- [ ] Add default Bandit excludes to profiles
- [ ] Create summary output mode for Bandit

### Phase 3: UX Improvements (Following Sprint)
- [ ] Add plain English gate summary
- [ ] Add config preview before writing
- [ ] Add diff view for updates to existing configs

## Files to Modify

| File | Change |
|------|--------|
| `cihub/wizard/core.py` | Add profile selection step |
| `cihub/wizard/questions/profile.py` | **NEW** - Profile selection prompts |
| `cihub/wizard/questions/python_tools.py` | Make conditional on "Custom" |
| `cihub/wizard/questions/java_tools.py` | Make conditional on "Custom" |
| `cihub/commands/setup.py` | Integrate profile selection |
| `templates/profiles/*.yaml` | Add `mode`, `exclude` settings |

## ADR Reference

This plan should be formalized in an ADR:
- **ADR-00XX:** Wizard Profile-First Design
- **Decision:** Wizard presents profiles before individual tools
- **Rationale:** Reduces cognitive load, leverages existing profile definitions

## Related Docs

- `templates/profiles/README.md` - Profile definitions
- `docs/development/active/REGISTRY_AUDIT_AND_PLAN.md` - Registry ↔ Wizard integration
- `docs/development/MASTER_PLAN.md` - Priority #2 includes wizard improvements
