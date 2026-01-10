# README Audit Report

> **Generated: 2026-01-09** | 8 agents used for comprehensive audit

---

## Executive Summary

| Area | Status | Issues Found |
|------|--------|--------------|
| README Links | PASS | All 11 links valid and have content |
| CLI Commands | FAIL | 10+ essential commands missing from README |
| Technical Claims | PARTIAL | Tool lists incomplete, env vars missing |
| GETTING_STARTED.md | PARTIAL | Command syntax errors, missing commands |
| CLI.md | PASS | Generated, complete, accurate |
| TROUBLESHOOTING.md | FAIL | Missing debugging flags, triage bundles, exit codes |
| TOOLS.md | FAIL | Hand-written (not generated), missing tools, missing config options |

---

## Part 1: README Issues

### Missing Essential CLI Commands

These commands are **core to the CLI** but not mentioned in README:

| Command | Purpose | Priority |
|---------|---------|----------|
| `check` | Pre-push validation (5 tiers) | MUST ADD |
| `triage` | Analyze CI failures | MUST ADD |
| `validate` | Validate .ci-hub.yml against schema | MUST ADD |
| `detect` | Detect repo language | SHOULD ADD |
| `run` | Run single tool with JSON output | SHOULD ADD |
| `docs generate/check/stale` | Doc automation | SHOULD ADD |
| `verify` | Verify workflow contracts | SHOULD ADD |
| `scaffold` | Generate fixture projects | MENTION |
| `smoke` | Local smoke test | MENTION |
| `registry` | Tier management | MENTION |

### Incomplete Tool Lists

**Python tools missing from README:**
- sbom
- semgrep (listed as Shared but also in Python)
- trivy (listed as Shared but also in Python)
- codeql (listed as Shared but also in Python)
- docker (listed as Shared but also in Python)

**Java tools missing from README:**
- sbom
- jqwik (mentioned but not in table)
- semgrep, trivy, codeql, docker (shared tools)

### Missing Environment Variables

README lists 3 env vars, but there are more:

| Variable | Purpose | In README? |
|----------|---------|------------|
| CIHUB_DEBUG | Tracebacks | Yes |
| CIHUB_VERBOSE | Tool logs | Yes |
| CIHUB_EMIT_TRIAGE | Triage bundle | Yes |
| CIHUB_DEBUG_CONTEXT | Decision blocks | NO |
| CIHUB_WRITE_GITHUB_SUMMARY | GH summary | NO |
| CIHUB_REPORT_INCLUDE_DETAILS | Report details | NO |

---

## Part 2: Linked Docs Issues

### GETTING_STARTED.md (Grade: B+)

**Issues Found:**

1. **Command syntax errors** (lines 426-431):
   ```bash
   # WRONG in docs:
   cihub config --repo <name> show

   # CORRECT:
   cihub config show --repo <name>
   ```

2. **Missing commands:**
   - `cihub setup` (interactive wizard) - not in Key Commands table
   - `cihub new` - creates hub-side configs, not documented
   - `cihub discover` - generates repo matrix, not documented
   - `cihub hub` - operational settings, not documented

3. **Missing report subcommands:**
   - `aggregate`, `dashboard`, `validate` not documented

4. **Inaccurate claim:**
   - `cihub run` says "(Python only)" - WRONG, supports both languages

### TROUBLESHOOTING.md (Grade: C)

**Major Gaps:**

1. **No debugging flags section** - CIHUB_DEBUG, CIHUB_VERBOSE, etc. not documented
2. **No triage bundles explanation** - users won't know about .cihub/triage.json
3. **No exit codes** - 0, 1, 2, 3, 4, 130 not explained
4. **No tool-outputs directory** - .cihub/tool-outputs/ not mentioned
5. **No timeout documentation** - CommandTimeoutError not covered
6. **Broken reference** - RESEARCH_LOG.md path doesn't exist

**Missing Error Scenarios:**
- ConfigValidationError
- CommandNotFoundError
- CommandTimeoutError
- JSON parse errors
- Missing tool installations

### TOOLS.md (Grade: C-)

**Critical Issues:**

1. **Not generated** - Hand-written, will drift from code
2. **Missing tools:**
   - docker (both Java and Python)
   - sbom (both Java and Python)
   - jqwik (Java) - mentioned but not detailed

3. **Missing config options for ALL tools:**
   - `require_run_or_fail` - not documented anywhere
   - `fail_on_*` variants - incomplete
   - `max_errors`, `max_issues`, `max_violations` - missing

4. **Should be auto-generated** from:
   - `cihub/tools/registry.py`
   - `schema/ci-hub-config.schema.json`

### CLI.md (Grade: A)

- Generated correctly
- All 33 commands documented
- All subcommands present
- Descriptions accurate

### Other Docs (All PASS)

- docs/README.md - Complete index
- docs/reference/CONFIG.md - Generated, accurate
- .github/CONTRIBUTING.md - Good command matrix
- .github/SECURITY.md - Minimal but acceptable
- LICENSE - Complete Elastic 2.0

---

## Part 3: README Best Practices (From Research)

### What's Missing vs. Best Practice

| Best Practice | Current README | Recommendation |
|---------------|----------------|----------------|
| Quick "zero to working" example | Has setup/init/ci | Add expected output |
| Features list | Problem/Solution table | Good, keep it |
| Common use cases | Execution modes | Add "Pre-Push Validation" |
| Troubleshooting link | Not prominent | Add mini-section with link |
| Platform support | Prerequisites section | Good |
| Visual/diagram | None | Consider ASCII hub→repo diagram |

### Sections to Add

1. **Pre-Push Validation** - `cihub check` tiers
2. **Debugging** - Expand with triage command
3. **Local Testing** - scaffold, smoke, verify
4. **Configuration Management** - detect, validate, config, registry

---

## Part 4: Recommended README Changes

### Add This Section After "Quick Start"

```markdown
## Pre-Push Validation

| Tier | Command | Time | What It Checks |
|------|---------|------|----------------|
| Fast | `cihub check` | ~30s | lint, format, type, test, actionlint |
| Audit | `cihub check --audit` | ~45s | + links, adr, configs |
| Security | `cihub check --security` | ~2min | + bandit, pip-audit, trivy |
| Full | `cihub check --full` | ~3min | + templates, matrix, license |
| All | `cihub check --all` | ~15min | + mutation testing |
```

### Expand "Debugging & Triage" Section

```markdown
## Debugging & Triage

| Flag | Effect |
|------|--------|
| `CIHUB_DEBUG=True` | Show tracebacks |
| `CIHUB_VERBOSE=True` | Show tool logs |
| `CIHUB_DEBUG_CONTEXT=True` | Show decision blocks |
| `CIHUB_EMIT_TRIAGE=True` | Write triage bundle |

### Triage CI Failures

```bash
# Analyze latest failed run
cihub triage --latest

# Or analyze specific run
cihub triage --run <run-id>

# Outputs: .cihub/triage.json, priority.json, triage.md
```
```

### Add "Local Testing" Section

```markdown
## Local Testing

```bash
# Generate a test fixture project
cihub scaffold --type python

# Validate schema and config
cihub validate --repo .

# Run a single tool
cihub run ruff --repo .

# Smoke test (detect → init → validate → ci)
cihub smoke --repo .
```
```

### Fix Tool Tables

Add these to Python table:
- sbom
- docker

Add these to Java table:
- sbom
- docker
- jqwik (expand from just mention)

---

## Part 5: Action Items

### Immediate (README)

- [ ] Add `check` command with tier table
- [ ] Add `triage` command for CI failures
- [ ] Add `validate` command
- [ ] Add missing debugging flags (CIHUB_DEBUG_CONTEXT)
- [ ] Fix tool tables (add docker, sbom, jqwik)
- [ ] Add "Local Testing" section

### Short-term (Linked Docs)

- [ ] Fix GETTING_STARTED.md command syntax (--repo position)
- [ ] Add missing commands to GETTING_STARTED.md Key Commands
- [ ] Add debugging section to TROUBLESHOOTING.md
- [ ] Add triage bundle explanation to TROUBLESHOOTING.md
- [ ] Add exit codes to TROUBLESHOOTING.md
- [ ] Remove broken RESEARCH_LOG.md reference

### Medium-term (Generation)

- [ ] Generate TOOLS.md from registry + schema (currently hand-written)
- [ ] Add `require_run_or_fail` to all tool docs
- [ ] Document all `fail_on_*` config options

---

## Appendix: All Verified Links

| Link | File | Status |
|------|------|--------|
| docs/README.md | Docs Index | VALID (94 lines) |
| docs/guides/GETTING_STARTED.md | Getting Started | VALID (771 lines) |
| docs/reference/CLI.md | CLI Reference | VALID (2,323 lines, generated) |
| docs/reference/CONFIG.md | Config Reference | VALID (123 lines, generated) |
| docs/reference/TOOLS.md | Tools Reference | VALID (696 lines, hand-written) |
| docs/guides/TROUBLESHOOTING.md | Troubleshooting | VALID (489 lines) |
| docs/development/DEVELOPMENT.md | Development Guide | VALID (357 lines) |
| docs/development/status/STATUS.md | Current Status | VALID (147 lines) |
| .github/CONTRIBUTING.md | Contributing | VALID (70 lines) |
| .github/SECURITY.md | Security | VALID (16 lines) |
| LICENSE | License | VALID (58 lines) |
