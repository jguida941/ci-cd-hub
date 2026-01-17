# ADR-0048: Documentation Automation Strategy

**Status**: Accepted  
**Date:** 2026-01-06  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-06  

> **Living Document Note:** This ADR covers the overall documentation automation strategy.
> As new documentation automation commands are added (e.g., `docs coverage`, `docs drift`),
> they should be documented here rather than creating separate ADRs.

## Context

Documentation drifts from code over time. Common problems:

1. **Stale references**: Docs mention functions, classes, or files that have been renamed/deleted
2. **Broken links**: Internal markdown links point to moved/deleted files
3. **Outdated examples**: Code examples no longer match the actual implementation
4. **Missing coverage**: New features lack documentation

Manual documentation reviews are:
- Time-consuming and error-prone
- Often skipped under deadline pressure
- Inconsistent across team members

## Decision

Implement a suite of automated documentation quality tools under the `cihub docs` command family:

### Command Suite

| Command | Purpose | Status |
|---------|---------|--------|
| `docs generate` | Generate CLI and config reference docs from code | [x] Implemented |
| `docs check` | Verify generated docs are up-to-date | [x] Implemented |
| `docs links` | Check for broken internal/external links | [x] Implemented |
| `docs stale` | Detect references to removed/renamed code | [x] Implemented |
| `docs audit` | Validate lifecycle, ADR metadata, and doc references | [x] Implemented |

### Architecture

```
cihub/commands/
├── docs/  # generate, check, links handlers (package)
├── docs_stale/ # Modular package (reference pattern)
│ ├── __init__.py # Main handler
│ ├── types.py # CodeSymbol, DocReference, StaleReport
│ ├── extraction.py # Symbol/reference extraction
│ ├── git.py # Git operations (compare, file status)
│ ├── comparison.py # Stale reference detection
│ └── output.py # Output formatting (JSON, markdown, GitHub)
├── docs_audit/ # Modular package (Part 12.J)
│ ├── __init__.py # Main handler
│ ├── types.py # AuditFinding, AuditReport, ADRMetadata
│ ├── lifecycle.py # STATUS.md ↔ active/ sync validation
│ ├── adr.py # ADR metadata linting
│ ├── references.py # Plain-text docs/ path scanning
│ └── output.py # Output formatting (JSON, markdown, GitHub)
```

### Design Principles

1. **Git-based detection**: Use `git diff` to identify changed symbols, then scan docs for stale references
2. **AI-consumable output**: `--ai` flag produces markdown suitable for LLM consumption
3. **CI integration**: `--fail-on-stale` for gating PRs on documentation freshness
4. **Modular packages**: Complex commands (like `docs stale`) use package structure for testability

### `docs stale` Implementation Details

The `docs stale` command detects when documentation references code that no longer exists:

```bash
# Basic usage - check last 10 commits
cihub docs stale

# CI mode - fail if stale refs found
cihub docs stale --fail-on-stale

# AI-friendly output for LLM review
cihub docs stale --ai --ai-output=stale-refs.md

# Custom scope
cihub docs stale --since=main --code=src --docs=documentation
```

**Detection strategy:**
1. Parse `git diff` to find deleted/renamed functions, classes, files
2. Scan markdown files for references (inline code, links, code fences)
3. Match references against deleted symbols
4. Report with file:line locations and suggested fixes

**Output formats:**
- Human-readable summary (default)
- JSON (`--json`) for programmatic consumption
- AI markdown pack (`--ai`) for LLM-assisted fixes
- GitHub Step Summary (`--github-summary`)

### `docs audit` Implementation Details

The `docs audit` command validates documentation structure and metadata:

```bash
# Basic usage - full audit
cihub docs audit

# Fast mode - skip reference scanning
cihub docs audit --skip-references

# Write artifacts for triage integration
cihub docs audit --output-dir .cihub/tool-outputs

# CI mode with GitHub summary
cihub docs audit --github-summary
```

**Validation checks:**
1. **Lifecycle**: Files in `active/` must be listed in STATUS.md, and vice versa
2. **Archive headers**: Archived docs must have "Superseded" headers
3. **ADR metadata**: Required fields (Status, Date), valid status values, Superseded-by for superseded ADRs
4. **References**: Plain-text `docs/...` paths must point to existing files

**Output formats:**
- Human-readable summary (default)
- JSON (`--json`) for programmatic consumption
- Artifacts (`--output-dir`) writes `docs_audit.json`
- GitHub Step Summary (`--github-summary`)

**CI Integration:**
- Wired into `cihub check --audit` tier
- Runs with `--skip-references` for speed in CI

### CI Integration

```yaml
# In .github/workflows/docs.yml
- name: Check documentation freshness
 run: |
 cihub docs stale --fail-on-stale --github-summary
 cihub docs audit --github-summary
```

## Consequences

### Positive

- **Early detection**: Catch stale docs before they reach users
- **CI enforcement**: Documentation quality becomes a merge requirement
- **Developer productivity**: Automated detection vs. manual review
- **AI assistance**: Output format optimized for LLM-based fix suggestions
- **Consistency**: Single source of truth for documentation standards

### Negative

- **False positives**: Common names may trigger incorrect matches
- **Git dependency**: Requires git history for `docs stale`
- **Learning curve**: Team must understand which flags to use in CI

### Mitigations

- `--skip-fences` to reduce false positives in code examples
- Exclude patterns for known false positives (via `.ci-hub.yml`)
- Clear `--help` documentation for each subcommand

## Future Commands

This ADR will be updated as new documentation automation commands are added:

- [ ] `docs coverage` - Report documentation coverage for public API
- [ ] `docs drift` - Detect semantic drift (docs describe different behavior than code)
- [ ] `docs toc` - Auto-generate/validate table of contents

## Test Coverage

- `tests/test_commands_docs.py` - docs generate/check tests
- `tests/test_docs_stale/` - 63 tests including 15 Hypothesis property-based tests
- `tests/test_docs_audit/` - (planned) lifecycle, ADR, reference validation tests

## Files Changed

- `cihub/cli_parsers/docs.py` - Parser definitions for all docs subcommands
- `cihub/commands/docs/` - Modular package (generate, check, links handlers)
- `cihub/commands/docs_stale/` - Modular package (6 files)
- `cihub/commands/docs_audit/` - Modular package (5 files)
- `cihub/commands/check.py` - Integration into `check --audit` tier

## Related ADRs

- ADR-0042: CommandResult Pattern (output structure)
- ADR-0043: Triage Service Modularization (package pattern reference)
- ADR-0046: OutputRenderer Pattern (output formatting)
