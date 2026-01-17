# Documentation Automation Audit & Design

**Status:** active
**Owner:** Development Team
**Source-of-truth:** manual
**Last-reviewed:** 2026-01-15

**Date:** 2026-01-04
**Last Updated:** 2026-01-10 (`docs audit` Part 13.U/W/X complete)
**Priority:** **#4** (See [MASTER_PLAN.md](../MASTER_PLAN.md#active-design-docs---priority-order))
**Status:** ~98% implemented (`docs stale` complete, `docs audit` complete with Part 12.J/L/N/Q + Part 13.R/S/T/U/V/W/X)
**Depends On:** Stable CLI surface (CLEAN_CODE.md archived)
**Can Parallel:** TEST_REORGANIZATION.md (both need stable CLI)
**Problem:** Manual documentation updates take 4+ hours/day. With 50+ docs and 28,000 lines, keeping them in sync with code changes is unsustainable.

---

## Implementation Status (2026-01-10)

| Component | Status | Notes |
|-----------|--------|-------|
| `cihub docs generate` | [x] **IMPLEMENTED** | Generates CLI.md, CONFIG.md, ENV.md, WORKFLOWS.md |
| `cihub docs check` | [x] **IMPLEMENTED** | Drift detection for generated docs |
| `cihub docs links` | [x] **IMPLEMENTED** | Internal link validation |
| `cihub docs stale` | [x] **IMPLEMENTED** | Modularized package (957→1489 lines across 6 modules), 63 tests |
| `cihub docs audit` | [x] **COMPLETE** | Core checks (J/L/N/Q) + Part 13.R/S/T/U/V/W/X complete; optional items remain |
| `.cihub/tool-outputs/` for docs | [x] **IMPLEMENTED** | `docs audit --output-dir` wired into `check --audit` (fast mode - no refs/consistency) |
| AI prompt pack output | WARNING: **OPTIONAL SUPPORT** | `docs stale --ai` or `--ai-output PATH` implemented |
| Specs hygiene | [x] **IMPLEMENTED** | Part 12.J - REQUIREMENTS.md Status/Last Updated headers |
| Metrics drift detection | [x] **IMPLEMENTED** | Part 13.R - detect stale counts in docs vs actual |
| Duplicate task detection | [~] **DISABLED** | Part 13.S - fuzzy matching implemented but disabled pending cleanup (too noisy) |
| Timestamp freshness | [x] **IMPLEMENTED** | Part 13.T - "Last Updated" header staleness |
| Placeholder detection | [x] **IMPLEMENTED** | Part 13.V - markers (YOUR_*, TODO:), local paths (GitHub usernames disabled - too noisy) |
| Checklist-reality sync | [x] **IMPLEMENTED** | Part 13.U - verify [ ] items against code |
| Cross-doc consistency | [x] **IMPLEMENTED** | Part 13.W - README.md ↔ active/ directory sync (limited scope) |
| CHANGELOG validation | [x] **IMPLEMENTED** | Part 13.X - format and ordering checks |
| Guide command validation | [ ] **NOT IMPLEMENTED** | Validate `cihub <command>` mentions in guides against CLI |

**Overall:** ~98% implemented. `docs stale` complete; `docs audit` complete (J/L/N/Q + Part 13.R/S/T/U/V/W/X). Only optional items remain.

**Implemented in `docs audit` (2026-01-09):**
- [x] active/ ↔ STATUS.md sync (Part 12.J)
- [x] Archive superseded header check with explicit reference requirement (Part 12.J)
- [x] Specs hygiene: REQUIREMENTS.md Status/Last Updated validation (Part 12.J)
- [x] ADR metadata lint: Status/Date/Superseded-by (Part 12.L)
- [x] Plain-text docs/ reference scanning (Part 12.N) - URL-aware, excludes archived/research docs
- [x] Universal doc header enforcement (Part 12.Q) - validates Status/Owner/Source-of-truth/Last-reviewed
- [x] --output-dir wired in check --audit → writes .cihub/tool-outputs/docs_audit.json
- [x] Metrics drift detection: stale counts in docs vs actual code (Part 13.R)
- [~] Duplicate task detection with fuzzy matching (Part 13.S) - implemented but disabled (too noisy pending task consolidation)
- [x] Timestamp freshness validation (Part 13.T)
- [x] Placeholder detection: markers (YOUR_*, TODO:), local paths (Part 13.V)
- [x] Checklist-reality sync: verify [ ] items against code implementations (Part 13.U)
- [x] Cross-doc consistency: README.md ↔ active/ directory sync (Part 13.W)
- [x] CHANGELOG validation: date ordering and duplicate detection (Part 13.X)

**NOT yet implemented in `docs audit` (optional):**
- [ ] Path-change update rules (Part 12.J)
- [ ] Doc inventory/counts (Part 12.M)
- [ ] Guide command validation: verify `cihub <command>` references in `docs/guides/` against CLI (new)

**Tests:** 39 tests in `tests/test_docs_audit.py` (types, lifecycle, ADR, references, consistency, headers, metrics, checklist-reality, cross-doc, changelog)

**Module structure:**
```
cihub/commands/docs_audit/
├── __init__.py # Main cmd_docs_audit entry point
├── types.py # Data models (AuditFinding, AuditReport, TaskEntry, etc.)
├── lifecycle.py # STATUS.md ↔ active/ sync validation
├── adr.py # ADR metadata linting
├── headers.py # Universal doc header enforcement (Part 12.Q)
├── references.py # Plain-text docs/ path scanning (URL-aware)
├── consistency.py # Part 13: duplicates, timestamps, placeholders
└── output.py # Output formatters (human, JSON, GitHub summary)
```

**Next Priority:** Optional items only (guide command validation, doc inventory/counts).

---

## 2026-01-15 Doc Audit Cleanup

- Added universal header blocks to manual docs (Status/Owner/Source-of-truth/Last-reviewed).
- Inserted explicit Superseded-by headers for archived docs.
- Normalized CHANGELOG duplicate date headings by demoting repeats to `###`.
- README active-doc parsing now accepts lowercase filenames (case-insensitive match).
- Docs audit clean as of 2026-01-15 (warnings limited to stale test counts and duplicate changelog dates).

---

## Known Documentation Contradictions (7-Agent Audit 2026-01-06)

> **Source:** Comprehensive 7-agent code review. Items marked ~~strikethrough~~ have been resolved.

| # | Issue | Files | Impact | Status |
|---|-------|-------|--------|--------|
| ~~1~~ | ~~CLI help snapshot missing registry command~~ | `tests/snapshots/cli_help.txt` | ~~Tests pass but snapshot stale~~ | **RESOLVED** |
| ~~2~~ | ~~TypeScript CLI design references `triage --ai` as planned behavior~~ | `docs/development/active/TYPESCRIPT_CLI_DESIGN.md` | ~~Design doc only; not a code mismatch~~ | **RESOLVED** |
| ~~3~~ | ~~ADR-0045 import path mismatch~~ | `docs/adr/0045-*` | ~~No mismatch; ADR uses exec_utils~~ | **RESOLVED** |
| ~~4~~ | ~~Schema version v1 in ADR but v2 in code~~ | `schema/triage.schema.json` | ~~ADR already references v2~~ | **RESOLVED** |
| ~~5~~ | ~~`--ai` flag for fix says "with --report" but not enforced~~ | `cihub/commands/fix.py` | ~~Flag validation already enforced~~ | **RESOLVED** |
| ~~6~~ | ~~Docs index omits active design docs~~ | `docs/README.md` | ~~Confusing entry point~~ | **RESOLVED** |

**Action:** Keep contradiction list in sync; add new findings to `cihub docs audit` rules when discovered.

---

## Index (Quick Navigation)

- [Part 1: Current Documentation Inventory](#part-1-current-documentation-inventory)
- [Part 2: How Your Current Automation Works](#part-2-how-your-current-automation-works)
- [Part 3: The Core Problem (Why Docs Go Stale)](#part-3-the-core-problem-why-docs-go-stale)
- [Part 4: The Solution Architecture](#part-4-the-solution-architecture)
- [Part 5: How Schemas Fit In](#part-5-how-schemas-fit-in)
- [Part 6: Implementation Plan](#part-6-implementation-plan)
- [Part 9: Finalized Implementation (`cihub docs stale`)](#part-9-finalized-implementation-cihub-docs-stale)
- [Part 11: Plan Review Findings & Gaps](#part-11-plan-review-findings--gaps)
- [Part 12: Audit Addendum (Production-Grade Revisions)](#part-12-audit-addendum-production-grade-revisions)
- [Part 13: Cross-Document Consistency & Metrics Validation](#part-13-cross-document-consistency--metrics-validation-audit-addendum-2026-01-06)

---
## Part 1: Current Documentation Inventory

### By Category

| Category | Files | Lines | Can Auto-Generate? |
|-------------------------|-------|--------|----------------------------------------------|
| ADRs | 37 | ~3,700 | [ ] No (architectural decisions require human) |
| Reference (CLI, Config, ENV, Workflows) | 4 | ~3,000 | [x] Yes (`cihub docs generate` does this) |
| Guides | 8 | ~2,300 | WARNING: Partially (examples can be validated) |
| Development/Status | 10+ | ~3,500 | WARNING: Partially (status can track code) |
| Archive | 15+ | ~5,000 | [ ] No (historical, shouldn't change) |
| Research | 1 | ~1,600 | [ ] No (notes, not synced to code) |

### Total: ~28,000 lines across 70+ files

---

## Part 2: How Your Current Automation Works

### 1. `cihub docs generate` (works well [x])

**Location:** `cihub/commands/docs/`

**How it works:**
```
┌─────────────────┐ ┌──────────────────┐ ┌─────────────┐
│ argparse parser │────▶│ _render_parser() │────▶│ CLI.md │
└─────────────────┘ └──────────────────┘ └─────────────┘

┌─────────────────────────┐ ┌────────────────────┐ ┌─────────────┐
│ schema/ci-hub-config. │────▶│ _schema_entries() │────▶│ CONFIG.md │
│ schema.json │ └────────────────────┘ └─────────────┘
└─────────────────────────┘
```

**Key insight:** This works because it extracts from **structured sources** (argparse, JSON schema). The schema defines the shape; the generator reads it and outputs markdown.

### 2. `cihub adr new` (works well [x])

**Location:** `cihub/commands/adr.py`

**How it works:**
- `_get_next_number()` scans existing files for the highest ADR number
- Creates from hardcoded template with auto-filled date
- Updates `docs/adr/README.md` index automatically

**Limitation:** The *content* of ADRs must be written by humans. The decision, context, and consequences are architectural judgment-no tool can generate those.

### 3. `cihub docs check` (detects drift [x])

**How it works:**
- Regenerates CLI.md and CONFIG.md in memory
- Compares against what's on disk
- If different → "Docs are out of date"

**This is the pattern you want to extend.**

---

## Part 3: The Core Problem (Why Docs Go Stale)

Docs reference code elements:
```markdown
# In GETTING_STARTED.md
Run `cihub scaffold python-pyproject /tmp/test` to create a fixture...
The `load_ci_config()` function merges defaults with repo config...
```

When code changes:
- Function renamed: `load_ci_config` → `load_config`
- Command removed: `cihub scaffold` → `cihub new`
- Behavior changed: now requires `--repo` flag

**But the docs still say the old thing.**

---

## Part 4: The Solution Architecture

### Concept: Code-to-Doc Reference Tracking

```
┌──────────────────────────────────────────────────────────────────┐
│ DOC FRESHNESS PIPELINE │
├──────────────────────────────────────────────────────────────────┤
│ │
│ 1. EXTRACT 2. INDEX 3. DIFF 4. ALERT │
│ ───────────────────────────────────────────────────────────── │
│ │
│ ┌─────────┐ ┌─────────────┐ ┌─────────┐ ┌─────────┐ │
│ │ Code │──────▶│ References │───▶│ Compare │──▶│ Stale │ │
│ │ Symbols │ │ Index │ │ to Git │ │ Report │ │
│ └─────────┘ └─────────────┘ │ Diff │ └─────────┘ │
│ │ ▲ └─────────┘ │ │
│ │ │ ▼ │
│ ┌─────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ Docs │──────▶│ Doc │ │ AI Update │ │
│ │ (.md) │ │ References │ │ (Optional) │ │
│ └─────────┘ └─────────────┘ └─────────────┘ │
│ │
└──────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Implementation

#### Step 1: Extract Code Symbols

Parse Python files for:
- Function names (`def foo(...)`)
- Class names (`class Bar:`)
- CLI commands (from argparse)
- Config keys (from schema)

```python
# Pseudocode
def extract_symbols(file: Path) -> set[str]:
 tree = ast.parse(file.read_text())
 symbols = set()
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
 symbols.add(node.name)
 if isinstance(node, ast.ClassDef):
 symbols.add(node.name)
 return symbols
```

#### Step 2: Extract Doc References

Scan markdown for code references:
- Backtick code: `load_ci_config`
- Code blocks with function calls
- File paths: `cihub/commands/docs/`

```python
def extract_doc_references(md_file: Path) -> dict[str, list[int]]:
 """Returns {reference: [line_numbers]}"""
 content = md_file.read_text()
 refs = {}
 for i, line in enumerate(content.splitlines(), 1):
 for match in re.findall(r'`([a-z_][a-z0-9_]*)`', line, re.I):
 refs.setdefault(match, []).append(i)
 return refs
```

#### Step 3: Compare to Git Diff

```bash
# What changed in the last commit?
git diff HEAD~1 --name-only -- "*.py"

# What symbols changed?
git diff HEAD~1 -- cihub/ | grep "^[-+]def \|^[-+]class "
```

#### Step 4: Find Stale Docs

```python
def find_stale_docs(changed_symbols: set[str]) -> list[dict]:
 stale = []
 for md_file in Path("docs").rglob("*.md"):
 refs = extract_doc_references(md_file)
 for symbol, lines in refs.items():
 if symbol in changed_symbols:
 stale.append({
 "file": str(md_file),
 "symbol": symbol,
 "lines": lines,
 "action": "REVIEW - symbol changed in code"
 })
 return stale
```

#### Step 5: AI Update (Optional)

Feed the stale report + git diff + doc content to Claude/GPT:

```
Context: The function `load_ci_config` was renamed to `load_config`.
File: docs/guides/GETTING_STARTED.md
Lines mentioning old name: 45, 67, 123

Current content at line 45:
"Use `load_ci_config(path)` to load the merged configuration..."

Please update this line to reflect the rename.
```

---

## Part 5: How Schemas Fit In

### What is a Schema?

A schema defines **the shape of data**. Your `ci-hub-config.schema.json`:

```json
{
 "properties": {
 "repo": {
 "properties": {
 "owner": { "type": "string" },
 "name": { "type": "string" }
 },
 "required": ["owner", "name"]
 },
 "language": {
 "enum": ["java", "python"]
 }
 },
 "required": ["repo", "language"]
}
```

This says: "A valid config MUST have `repo.owner`, `repo.name`, and `language`."

### Why Schemas Help Documentation

1. **Single source of truth**: Schema defines what's valid
2. **Auto-generate docs**: Your `cihub docs generate` reads schema → outputs CONFIG.md
3. **Validation**: When schema changes, `cihub docs check` catches it

### The Pattern

```
Schema (source of truth)
 ↓
cihub docs generate
 ↓
CONFIG.md (generated, never hand-edit)
 ↓
cihub docs check (CI gate)
 ↓
Fail build if stale
```

**Apply this pattern to more things:**
- CLI argparse → CLI.md (already done)
- Exit codes enum → EXIT_CODES.md (could add)
- Tool registry → TOOLS.md (could add)

---

## Part 6: Implementation Plan

### Phase 1: Stale Doc Detection (1-2 days)

Create `cihub docs stale`:

```bash
$ cihub docs stale --since HEAD~1

Stale Documentation Report
===========================
Changed symbols: load_ci_config → load_config, cmd_scaffold (removed)

docs/guides/GETTING_STARTED.md:
 Line 45: references `load_ci_config` (renamed)
 Line 123: references `cmd_scaffold` (removed)

docs/development/ARCHITECTURE.md:
 Line 67: references `load_ci_config` (renamed)

Run with --json for machine-readable output.
```

### Phase 2: Extend Auto-Generation (1 day)

Add more generated docs:
- `cihub docs generate --all`:
 - CLI.md (exists)
 - CONFIG.md (exists)
 - EXIT_CODES.md (new - from exit_codes.py)
 - COMMANDS.md (new - from command registry)

### Phase 3: AI Integration (2-3 days)

Create `cihub docs update --ai`:

```bash
$ cihub docs stale --since HEAD~1 --json > stale.json
$ cihub docs update --ai --input stale.json --dry-run

Would update:
 docs/guides/GETTING_STARTED.md (3 changes)
 docs/development/ARCHITECTURE.md (1 change)

Preview changes? [y/N]
```

Under the hood:
1. Read stale.json
2. For each file, extract context (surrounding lines)
3. Get git diff for changed symbols
4. Call Claude/GPT API with: "Update these references"
5. Apply changes (or show diff)

### Phase 4: CI Gate (1 day)

Add to `.github/workflows/hub-production-ci.yml`:

```yaml
- name: Check docs freshness
 run: |
 cihub docs check
 cihub docs stale --since ${{ github.event.before }} --fail-on-stale
```

---

## Part 7: What You CANNOT Automate

| Doc Type | Why Not |
|----------|---------|
| ADR decisions | Architectural judgment requires human |
| Guide prose | Explaining "why" requires understanding |
| Troubleshooting | Requires experience with real issues |
| Research notes | Personal investigation logs |

**These require human review.** The best you can do:
- Flag them as potentially stale
- Show what code changed
- Let a human (or AI with human review) update

---

## Part 8: Immediate Actions

### Today
1. [x] Run `cihub docs check` in CI (already possible)
2. [x] Run `cihub docs generate` before commits

### This Week
3. Create `cihub docs stale` command
4. Add symbol extraction from Python AST
5. Add reference extraction from Markdown

### Next Week
6. Integrate with git diff
7. Add AI update prototype
8. Add to CI pipeline

---

## Appendix: File Locations

| Purpose | File |
|---------|------|
| Docs generate/check | `cihub/commands/docs/` |
| ADR management | `cihub/commands/adr.py` |
| Schema | `schema/ci-hub-config.schema.json` |
| CLI parser | `cihub/cli_parsers/` |
| Exit codes | `cihub/exit_codes.py` |

---

---

## Part 9: Finalized Implementation (`cihub docs stale`)

### Scope / Non-goals (Clarification 2026-01-09)

> **Why this note exists:** The scope of `docs stale` has caused recurring confusion. This section clarifies exactly what the command does and does not do.

**In Scope (v1):**
- Detect **removed/renamed Python symbols** (functions, classes, constants) referenced in docs
- Detect **deleted/renamed file paths** referenced in docs (e.g., `cihub/commands/foo.py`)
- Detect **removed CLI commands/flags** (via CLI surface diff, not behavior changes)
- Work is driven by `--since` flag (defaults to `HEAD~10`): only symbols that changed in that git range are checked

**Not In Scope (v1):**
- **Semantic drift** - behavior changes where names remain the same (needs different techniques)
- **Metrics drift** - stale numeric claims like "80 tests" (see Part 13.R for future `docs audit` feature)
- **Cross-document consistency** - same fact appearing differently across docs (see Part 13.W)
- **Checklist-reality sync** - unchecked items that are actually done (see Part 13.U)

**Output Artifacts (optional, implemented):**
- `--output-dir DIR` → writes `docs_stale.json` + `docs_stale.prompt.md` to specified directory
- `--tool-output PATH` → writes JSON to explicit path (for triage integration)
- `--ai-output PATH` → writes AI prompt pack to explicit path
- These are **not wired into `cihub check --audit` by default** - that integration is a Phase 2 task

---

### Command Design

```bash
# Human-readable output
cihub docs stale --since HEAD~5

# JSON for scripts/CI
cihub docs stale --since HEAD~5 --json

# AI-consumable markdown (pipe to file)
cihub docs stale --since HEAD~5 --ai > stale-report.md

# Include archived docs
cihub docs stale --since HEAD~5 --all
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ cihub docs stale │
├─────────────────────────────────────────────────────────────┤
│ │
│ 1. EXTRACT SYMBOLS 2. EXTRACT DOC REFS │
│ ──────────────────── ──────────────────── │
│ cihub/**/*.py docs/**/*.md │
│ │ │ │
│ ▼ ▼ │
│ ast.parse() regex backticks │
│ - functions - `symbol_name` │
│ - classes - skip code blocks │
│ - constants - skip archive/ │
│ │ │ │
│ ▼ ▼ │
│ {name: CodeSymbol} [DocReference] │
│ │
│ 3. GIT DIFF 4. CORRELATE │
│ ──────────────────── ──────────────────── │
│ git diff --since match refs to changes │
│ git diff --name-status detect moved/deleted files │
│ │ │ │
│ ▼ ▼ │
│ changed_symbols stale_references │
│ moved_deleted_files │
│ │
│ 5. OUTPUT │
│ ──────────────────── │
│ --json → CommandResult.data │
│ --ai → Markdown prompt for LLM │
│ default → Human-readable summary │
│ │
└─────────────────────────────────────────────────────────────┘
```

### Key Functions

```python
# cihub/commands/docs_stale.py

def extract_python_symbols(file: Path) -> list[CodeSymbol]
 # Uses ast.parse(), extracts def/class/CONSTANTS

def extract_doc_references(file: Path) -> list[DocReference]
 # Regex for `backtick_refs` and file paths, skips code blocks

def get_git_changed_symbols(root: Path, since: str) -> set[str]
 # git diff --name-only, then parse changed lines

def get_git_moved_deleted_files(root: Path, since: str) -> dict[str, str]
 # git diff --name-status to detect R(ename), D(elete)

def find_stale_references(...) -> list[StaleReference]
 # Correlate: doc refs that mention changed symbols OR moved/deleted files

def cmd_docs_stale(args) -> int | CommandResult
 # Main handler with --json, --ai, human modes
 # Supports: --since, --all, --json, --ai
```

### Files to Create/Modify

| File | Action |
|------|--------|
| `cihub/commands/docs_stale.py` | **CREATE** - main logic |
| `cihub/cli_parsers/docs.py` | MODIFY - add `stale` subparser |
| `cihub/cli_parsers/types.py` | MODIFY - add handler type |
| `cihub/cli.py` | MODIFY - add wrapper function |
| `tests/unit/docs/` | **CREATE** - tests |

### User Decisions (Confirmed)

1. **AI Output:** Stdout (pipe to file: `cihub docs stale --ai > report.md`)
2. **Skip archive:** Yes by default, `--all` flag includes everything
3. **Git range:** Flexible `--since` flag supports both `HEAD~N` and `origin/main..HEAD`
4. **File detection:** Yes - detect both symbol changes AND moved/deleted file references

---

## Part 10: Testing Strategy

### Principle: Test in Isolation First

We will NOT touch any real docs until the tool is proven to work.

### Phase 1: Unit Tests (`tests/unit/docs/`)

```python
class TestSymbolExtraction:
 def test_extracts_functions(self):
 # Create temp .py file with known functions
 # Assert symbols extracted match

 def test_extracts_classes(self):
 # Same pattern

 def test_extracts_constants(self):
 # UPPER_CASE names

class TestDocReferenceExtraction:
 def test_finds_backtick_refs(self):
 # Markdown with `symbol_name`

 def test_skips_code_blocks(self):
 # References inside ``` blocks should be skipped

 def test_finds_file_paths(self):
 # cihub/commands/docs.py references

class TestGitDiffParsing:
 def test_detects_renamed_function(self, mock_subprocess):
 # Mock git diff output with -def old_name / +def new_name

 def test_detects_deleted_file(self, mock_subprocess):
 # Mock git diff --name-status with D prefix

class TestStaleCorrelation:
 def test_flags_changed_symbol_reference(self):
 # Symbol in changed_symbols + doc references it = stale

 def test_flags_deleted_file_reference(self):
 # File deleted + doc references it = stale

 def test_ignores_unchanged_symbols(self):
 # Symbol NOT in changed_symbols = not stale
```

### Phase 2: Integration Test (Isolated Directory)

Create a test fixture in `tests/fixtures/doc_stale_test/`:

```
tests/fixtures/doc_stale_test/
├── code/
│ ├── module_a.py # Has: def old_function(), class OldClass
│ └── module_b.py # Has: def stable_function()
├── docs/
│ ├── guide.md # References: `old_function`, `stable_function`
│ └── readme.md # References: `OldClass`, `module_a.py`
└── .git/ # Fake git history
```

### Phase 3: Manual Smoke Test

Before running on real docs:
```bash
# Create isolated test
mkdir /tmp/doc-stale-test
cd /tmp/doc-stale-test
git init

# Create fake code
echo 'def original_name(): pass' > module.py
git add . && git commit -m "initial"

# Create fake doc
echo 'Use `original_name` to do things' > doc.md
git add . && git commit -m "add doc"

# Rename function
echo 'def new_name(): pass' > module.py
git add . && git commit -m "rename"

# Run tool
cihub docs stale --since HEAD~1 --code . --docs .
# Expected: "doc.md:1 references `original_name` (symbol changed)"
```

### Phase 4: Dry Run on Real Codebase

Once unit + integration tests pass:
```bash
# Run on real codebase but only OUTPUT, don't change anything
cihub docs stale --since HEAD~10 --json > /tmp/stale-report.json

# Review the report manually
cat /tmp/stale-report.json | jq '.stale_references | length'
# If reasonable number, inspect a few manually to verify accuracy
```

### Success Criteria

1. [x] Unit tests pass for all extraction functions
2. [x] Integration test catches known stale references
3. [x] Manual smoke test works in isolated directory
4. [x] Dry run on real codebase produces sensible output
5. [x] No false positives for common patterns (e.g., `true`, `false`, file extensions)

---

## Part 11: Plan Review Findings & Gaps

### High Priority Issues

| Issue | Impact | Resolution |
|-------|--------|------------|
| **False positives for new symbols** | `find_stale_docs` uses a single `changed_symbols` set and flags ANY matching reference. Newly added symbols will be falsely flagged as "changed". | Track removed/renamed vs added separately. Compare old vs new symbol sets. Emit rename pairs explicitly. |
| **Reference extraction too narrow** | Only matches backticked snake_case and explicitly skips fenced blocks. Misses: CLI commands, flags, dotted config keys, env vars, CLI examples in code fences. | Expand token patterns. Consider parsing code fences (at least bash/shell) for CLI examples. |

### Medium Priority Issues

| Issue | Impact | Resolution |
|-------|--------|------------|
| **CLI/Config changes not detected** | Plan says CLI commands (argparse) and config keys (schema) are in scope, but diff parsing only scans Python `def`/`class` lines. Parser/schema changes won't surface. | Add structured diffing: compare `cihub --help` output before/after, compare schema paths before/after. |
| **CLI surface inconsistent** | CI expects `--fail-on-stale`, smoke test uses `--code`/`--docs`, but command design omits these flags. | Define complete flag set: `--since`, `--all`, `--json`, `--ai`, `--fail-on-stale`, `--code`, `--docs` |
| **No local parity path** | Workflow changes proposed without a matching local command (`cihub check --audit` or `cihub audit`). Workflow edits require explicit approval. | Add CLI step locally before wiring CI. Consider `cihub check --docs-stale` or similar. |
| **Contract/snapshot updates missing** | Plan doesn't mention CLI parser contract or help snapshot updates required for new CLI commands. | Add to files list: `tests/snapshots/cli_help.txt`, parser contract tests. |

### Architectural Decisions (Finalized)

#### Decision 1: Code Fence Parsing

**Decision:** Parse bash/shell/console fences by default; skip other language fences.

**Rationale:**
- Existing `docs.py` and `adr.py` use `_strip_fenced_blocks()` to avoid false positives in link checking
- BUT the primary use case for `docs stale` is catching CLI drift in examples like:
 ```bash
 cihub scaffold python-pyproject /tmp/test # This could be stale
 ```
- CLI examples are almost always in bash/shell fences
- Python code examples in fences (like the pseudocode in Part 4) should be skipped - they're illustrative, not executable

**Implementation:**
```python
# Parse these fence types for CLI references:
PARSED_FENCE_TYPES = {"bash", "shell", "console", "sh", "zsh", ""} # "" = untagged fences

# Skip these fence types entirely:
SKIPPED_FENCE_TYPES = {"python", "json", "yaml", "xml", "java", ...}
```

**Flag:** `--skip-fences` to disable fence parsing entirely (for edge cases)

---

#### Decision 2: Generated Docs Exclusion

**Decision:** Exclude `docs/reference/` by default. Include root `README.md`.

**Rationale:**
- `docs/reference/` contains CLI.md, CONFIG.md, TOOLS.md, ENV.md, WORKFLOWS.md - all auto-generated by `cihub docs generate`
- These are already checked by `cihub docs check` which compares against regenerated content
- Running staleness check on generated docs is circular - they're BY DEFINITION current (regenerated from source)
- Root `README.md` is handwritten and references code symbols - it CAN become stale

**Implementation:**
```python
DEFAULT_EXCLUDE_PATTERNS = [
 "docs/reference/**", # Generated docs - use `cihub docs check` instead
 "docs/development/archive/**", # Archived docs - historical, shouldn't change
]

# Root README.md is INCLUDED by default (handwritten, can become stale)
```

**Flags:**
- `--all` includes archived docs
- `--include-generated` includes `docs/reference/` (rarely needed)

---

#### Decision 3: Default `--since` Behavior

**Decision:** Default to `HEAD~10`. Error with EXIT_USAGE if git ref can't resolve.

**Rationale:**
- Matches codebase pattern: sensible defaults + clear errors for bad input
- `HEAD~10` covers typical development cycle without being overwhelming
- Commands like `templates.py`, `pom.py`, `run.py` all use EXIT_USAGE with clear messages for invalid input
- No silent fallbacks - fail clearly so user knows what went wrong

**Implementation:**
```python
DEFAULT_SINCE = "HEAD~10"

# In cmd_docs_stale:
try:
 # Verify git ref resolves
 subprocess.run(["git", "rev-parse", since], check=True, capture_output=True)
except subprocess.CalledProcessError:
 message = f"Invalid git reference: {since}"
 if json_mode:
 return CommandResult(exit_code=EXIT_USAGE, summary=message)
 print(message, file=sys.stderr)
 return EXIT_USAGE
```

**Error cases:**
- `--since nonexistent_ref` → EXIT_USAGE: "Invalid git reference: nonexistent_ref"
- Not a git repo → EXIT_USAGE: "Not a git repository"

---

#### Decision 4: AI Output Mode

**Decision:** Prompt-only (no network). The `--ai` flag outputs markdown to stdout.

**Rationale:**
- Codebase makes NO network calls from CLI commands (except `gh` which is user-initiated external tool)
- The `--ai` flag produces AI-consumable markdown that can be:
 1. Piped to a file: `cihub docs stale --ai > stale-report.md`
 2. Fed to Claude/GPT externally (user's choice of tool/model)
 3. Used in automation pipelines
- Network-calling AI integration would be a significant architectural change requiring:
 - API key management
 - Rate limiting
 - Error handling for network failures
 - User consent for data transmission

**Implementation:**
```python
def _format_ai_output(report: StaleReport) -> str:
 """Format report as AI-consumable markdown.

 Output is designed to be fed to Claude/GPT externally.
 NO network calls are made by this command.
 """
 # ... generate markdown with context, diffs, instructions
```

**Future Phase (if needed):**
- Phase 4+ could add `cihub docs update --ai-apply` that calls API
- Would require explicit `--api-key` or env var
- Would require `--yes` or interactive confirmation
- NOT in scope for initial implementation

### Testing Additions Required

#### Contract/Snapshot Updates
- `tests/snapshots/cli_help.txt` - regenerate after adding `docs stale` subcommand
- `tests/test_module_structure.py` - add `cmd_docs_stale` to CLI facade exports if needed
- `tests/test_cli_commands.py` - add basic invocation test

#### Unit Tests for Reference Extraction
```python
class TestDocReferenceExtraction:
 # EXISTING (from Part 10)
 def test_finds_backtick_refs(self): ...
 def test_skips_code_blocks(self): ...
 def test_finds_file_paths(self): ...

 # NEW - expanded coverage
 def test_finds_cli_commands_in_prose(self):
 # e.g., "Run `cihub docs stale`" in paragraph

 def test_finds_cli_flags(self):
 # e.g., `--since`, `--json`, `--fail-on-stale`

 def test_finds_dotted_config_keys(self):
 # e.g., `repo.owner`, `python.pytest.enabled`

 def test_finds_env_vars(self):
 # e.g., `CIHUB_DEBUG`, `CI_HUB_TOKEN`

 def test_filters_common_false_positives(self):
 # e.g., `true`, `false`, `None`, `http://`, file extensions
```

#### Unit Tests for Baseline Comparison (Replace Diff-Hunk Parsing)
```python
class TestBaselineDetection:
 def test_compares_ast_sets_base_vs_head(self):
 # For a changed .py file:
 # - base symbols from `git show <base>:path.py` (AST parse)
 # - head symbols from working tree `path.py` (AST parse)
 # Assert: removed = base - head; added = head - base

 def test_never_flags_added_symbols_as_stale(self):
 # Added-only symbols must not generate stale refs

 def test_handles_unparseable_python_gracefully(self):
 # If ast.parse fails for base or head, emit a clear problem entry and continue

 def test_handles_invalid_since_gracefully(self):
 # e.g., --since nonexistent_ref -> EXIT_USAGE

 def test_handles_missing_git_gracefully(self):
 # Running in non-git directory -> EXIT_USAGE


class TestStructuredSources:
 def test_schema_key_diff_base_vs_head(self):
 # Compare schema keys derived from schema JSON (base vs head)
 # Assert: removed keys are detected; added keys do not trigger staleness

 def test_cli_surface_diff_base_vs_head(self):
 # Compare CLI help surface (base vs head) for removed commands/flags
 # Suggestion source can be tests/snapshots/cli_help.txt (versioned)


class TestFileMoves:
 def test_detects_deleted_and_renamed_files(self):
 # Use `git diff --name-status --find-renames <base>..HEAD` output parsing
 # Assert: docs referencing deleted paths are flagged
```

#### Integration Test
```python
class TestDocsStaleIntegration:
 def test_full_flow_with_temp_repo(self, tmp_path):
 # 1. Create temp git repo
 # 2. Add code + docs
 # 3. Rename a function
 # 4. Run cihub docs stale --since HEAD~1
 # 5. Verify stale reference detected

 def test_fail_on_stale_exit_code(self, tmp_path):
 # Verify --fail-on-stale returns non-zero when stale found

 def test_json_output_schema(self, tmp_path):
 # Verify JSON output has expected structure
```

### Revised Files to Create/Modify

| File | Action | Notes |
|------|--------|-------|
| `cihub/commands/docs_stale.py` | **CREATE** | Main logic with all extraction/diff functions |
| `cihub/cli_parsers/docs.py` | MODIFY | Add `stale` subparser with full flag set |
| `cihub/cli_parsers/types.py` | MODIFY | Add `cmd_docs_stale` handler type |
| `cihub/cli.py` | MODIFY | Add `cmd_docs_stale` wrapper function |
| `tests/unit/docs/` | **CREATE** | Comprehensive tests per above |
| `tests/snapshots/cli_help.txt` | MODIFY | Regenerate after CLI changes |

### Finalized CLI Surface

```bash
# Complete flag set
cihub docs stale [OPTIONS]

Options:
 --since REF Git revision range (default: HEAD~10)
 --all Include archived docs (docs/development/archive/)
 --include-generated Include generated docs (docs/reference/) - rarely needed
 --json JSON output for scripts/CI
 --ai AI-consumable markdown output (no network calls)
 --fail-on-stale Exit non-zero if stale refs found (for CI)
 --code PATH Code directory (default: cihub/)
 --docs PATH Docs directory (default: docs/)
 --skip-fences Skip bash/shell code fences (default: parse them)
 --output-dir DIR Optional output dir for CIHub-style artifacts (e.g., .cihub/)
 --tool-output PATH Optional path to write tool-style JSON (for triage/tool-outputs)
 --ai-output PATH Optional path to write the AI prompt pack (markdown)
```

**Exit Codes:**
- `EXIT_SUCCESS (0)` - No stale references found
- `EXIT_FAILURE (1)` - Stale references found (with `--fail-on-stale`)
- `EXIT_USAGE (2)` - Invalid arguments (bad --since ref, not a git repo, etc.)

**JSON Output Schema:**
```json
{
 "git_range": "HEAD~10",
 "stats": {
 "changed_symbols": 12,
 "removed_symbols": 3,
 "added_symbols": 9,
 "renamed_symbols": 2,
 "deleted_files": 1,
 "renamed_files": 0,
 "stale_refs": 7
 },
 "changed_symbols": [...],
 "stale_references": [
 {
 "doc_file": "docs/guides/GETTING_STARTED.md",
 "doc_line": 45,
 "reference": "load_ci_config",
 "reason": "Symbol was removed",
 "suggestion": "Check if renamed to load_config",
 "context": "Use `load_ci_config(path)` to load..."
 }
 ]
}
```

### Implementation Order

1. [x] **Architectural decisions finalized** (Part 11)
2. ⬜ **Create `cihub/commands/docs_stale.py`** with:
 - Symbol extraction (AST-based, classifies added/removed/renamed)
 - Reference extraction (backticks + bash fences + file paths)
 - Baseline compare (base vs head) via `git show` for code/schemas/CLI surface + file move/delete detection
 - Correlation logic (only flag REMOVED/RENAMED, not ADDED)
 - Three output modes (human, JSON, AI markdown)
3. ⬜ **Wire CLI** - Update `cli_parsers/docs.py`, `cli_parsers/types.py`, `cli.py`
4. ⬜ **Create tests** - `tests/unit/docs/` with unit + integration tests
5. ⬜ **Update snapshots** - Regenerate `tests/snapshots/cli_help.txt`
6. ⬜ **Local validation** - Run on real codebase, verify output makes sense
7. ⬜ **Wire into CI** - Add to `cihub check` or as standalone CI step (after local validation)

---

## Part 12: Audit Addendum (Production-Grade Revisions)

This section folds in additional gaps + improvements needed to make `cihub docs stale` trustworthy at scale, integrate cleanly with existing CIHub tooling, and produce higher-quality AI-ready outputs.

### A. Tighten the Contract (Keep Signal High)

**Definition of “stale” (v1):** A doc reference is stale only if it points to something that was **removed/renamed**.

In scope for v1:
- **Removed/renamed Python symbols** (functions/classes/constants) in tracked code paths
- **Removed/renamed config keys** (derived from schema paths)
- **Removed/renamed CLI commands/flags** (CLI surface drift)
- **Deleted/renamed file paths** referenced by docs (e.g., `cihub/commands/foo.py`, `templates/...`)

Explicit non-goal (v1):
- **Semantic drift** where behavior changes but names remain the same (this needs different techniques)

### B. Replace Diff-Hunk Parsing with Baseline Comparison (Base vs Head)

Parsing `git diff` hunks for `def`/`class` lines is fragile and a major source of false positives/negatives.

Prefer:
- Resolve `--since` into a single **base commit** (for ranges, use merge-base)
- For each changed file, compare **base vs head**:
 - Python: `ast.parse(git show <base>:path.py)` vs `ast.parse(path.py)` and compute set diffs
 - Schema: load `schema/ci-hub-config.schema.json` at base and head and diff key paths (reuse schema traversal approach from `cihub/commands/docs/`)
 - CLI surface: diff a **versioned help snapshot** at base vs head (see `tests/snapshots/cli_help.txt`) to detect removed commands/flags

This matches the repo’s existing “single source → deterministic output → drift gate” strategy.

### C. Markdown Extraction Needs a Region Model

Regex-only scanning will be noisy. Treat markdown as regions:
- Prose
- Inline code spans (highest-signal for CLI/flags/config keys)
- Fenced blocks: capture `(lang, content)`

Default behavior:
- Parse only “CLI-like” fences: `bash`, `sh`, `shell`, `zsh`, `console`, and untagged fences
- Skip other fences (`python`, `yaml`, `json`, etc.) to avoid illustrative examples becoming “stale”

Optional library (recommended if we want less custom parsing risk):
- `markdown-it-py` (tokenizes inline code/fences/links reliably)

### D. AI Output: Model It After Existing `cihub triage` Prompt Packs

You already have an LLM-ready prompt pack pattern (`cihub triage` → `triage.md`). `docs stale --ai` should mirror that approach:

Required `--ai` characteristics:
- **Structured** and **bounded** output (add `--max-files`, `--max-items`, `--context-lines`)
- **Per-file packets** with:
 - file path + category (docs/README/guide/dev)
 - each stale item: line, reference, reason (removed/renamed/deleted), small context window
 - optional relevant diff snippet *filtered to the reference*
- **Explicit constraints** up front:
 - do not edit generated docs under `docs/reference/**`
 - do not change ADRs
 - keep code fences intact except for CLI examples
 - use “CLI” terminology (never internal nicknames)

#### D1. AI Execution Mode (Claude / Local LLM CLI; No Direct API Calls)

**Decision:** AI-assisted updates (if/when implemented) should be done via **external CLI tools** (e.g., Claude CLI or other local “LLM” CLIs) invoked by CIHub, not by directly calling model APIs from CIHub.

**Rationale:**
- Keeps CIHub consistent with “CLI is the product” and avoids embedding API key/network concerns into CIHub.
- Lets teams choose the model/tooling (`claude`, `llm`, editor-integrated CLIs, etc.) without changing CIHub internals.
- Keeps the initial v1 scope simple: prompt pack generation + drift detection.

**Proposed Phase 2 CLI surface:**
- `cihub docs update --llm-runner claude --input docs_stale.json --dry-run`
- `cihub docs update --llm-runner claude --input docs_stale.json --patch-output docs.patch`
- `cihub docs update --llm-runner none --input docs_stale.json` (equivalent to “prompt-only”)

**Guardrails (required):**
- Default to **`--dry-run`** and emit a patch; never auto-apply by default.
- Support `--patch-output` (unified diff) so changes are reviewable and applyable with `git apply --3way`.
- Capture reproducibility metadata into `.cihub/tool-outputs/`:
 - runner name + version (if available)
 - command line used (redact secrets)
 - prompt pack path used
 - patch output path and apply status (if applied)

### E. Integrate with Existing Tooling (CLI-First, No Workflow Logic)

Best-fit integration points:
- Add `docs stale` into **`cihub check --audit`** (drift-detection lane) once it’s trusted
- Optionally emit machine outputs under `.cihub/tool-outputs/` so `cihub triage` can surface docs drift in the same triage/priority ecosystem (category `docs`)

Avoid:
- “Fixing YAML” as the primary solution. Wire behavior into the CLI first, then let workflows remain thin wrappers.

### F. Testing Upgrades Required for “Production-Grade”

Beyond unit tests:
- **Snapshot tests** (syrupy):
 - `--json` payload schema + stability
 - `--ai` markdown prompt pack stability
- **Git-shape integration tests**:
 - `--since HEAD~N`
 - `--since A..B` (merge-base handling)
 - file delete/rename/move
- **Property / fuzz tests** (Hypothesis already present in CI extras):
 - random markdown with mixed backticks/fences/links to ensure no crashes and no region “leakage”
- **Performance budget**:
 - benchmark scanning ~28k doc lines so `cihub check --audit` stays fast enough to run routinely

### G. Use Git More Aggressively (Correctness + Safety)

Where Git helps most:
- **Resolve range input correctly**: accept `--since HEAD~10` and `--since origin/main..HEAD`, but internally resolve to a single base commit (merge-base for ranges).
- **Read base content safely**: use `git show <base>:path` for baseline content instead of parsing patch hunks.
- **Handle file moves/deletes**: use `git diff --name-status --find-renames <base>..HEAD` to catch doc references to renamed/deleted files.

Safety invariants to avoid “overwriting everything”:
- Only propose changes tied to **removed/renamed** tokens (never added-only).
- Prefer emitting a **small set of targeted edits** (per-file packets) rather than “rewrite sections”.
- Add bounded output controls (`--max-files`, `--max-items`, `--context-lines`) so AI prompts stay stable and reviewable.

### H. AI Feeding: Produce Patch-Safe Outputs, Not Just “Suggestions”

To make AI updates safe and reviewable, generate *apply-able* artifacts:
- **Prompt pack** (`--ai` / `--ai-output`): per-file packets with constraints + context windows.
- **Tool-style JSON** (`--tool-output`): stable machine contract to drive automation and tests.
- Optional future: **unified diff output** (`--patch-output`) that can be applied with `git apply --3way` (never auto-apply in v1).

Recommended “guardrails” for AI-driven patches:
- Include a per-file **precondition** in JSON/prompt: file path + expected blob/hash (or expected context snippet) so apply can fail fast if content drifted.
- Ensure outputs explicitly avoid generated docs (`docs/reference/**`) and ADR edits.

### I. CI Results → Docs Drift Workflow (Without Auto-Mutating in CI)

“Automation updates based on CI results” should be **artifact-driven**, not “CI edits your repo”.

Recommended CI pattern:
- Run `cihub docs check` (already deterministic drift gate for generated docs).
- Run `cihub docs stale` in **report-only** mode and emit artifacts:
 - `.cihub/tool-outputs/docs_stale.json`
 - `.cihub/tool-outputs/docs_stale.prompt.md`
- Let humans (or a separate, opt-in bot) review/apply patches.

Optional integration improvement (Phase 2+):
- Extend `cihub triage` to surface additional “non-report tools” found under `.cihub/tool-outputs/` as `docs` category notes/warnings, so the triage prompt pack directly includes docs drift context.

### J. `cihub docs audit` (Lifecycle + Structure Enforcement)

- **Command contract:** `cihub docs audit [--output-dir .cihub] [--json]`
 - Validates the doc lifecycle:
 - All design docs in progress live under `docs/development/active/`
 - Every file in `docs/development/active/` must be listed in `docs/development/status/STATUS.md`
 - Moves to `docs/development/archive/` must include a “Superseded” header pointing to the replacement/ADR
 - Any path change for docs in `active/` or `archive/` must update `docs/README.md`, `docs/development/MASTER_PLAN.md`, and `docs/development/status/STATUS.md` in the same change
 - Specs hygiene: only `docs/development/specs/REQUIREMENTS.md` is active; it must include `Status` and `Last Updated`
 - Checks ADR metadata (Status/Date/Superseded-by), universal headers, and broken references (see Section N)
 - Emits `docs_audit.json` under `.cihub/tool-outputs/`
- **Integration:** runs automatically inside `cihub check --audit` in **fast mode** (skips `--references` and `--consistency` checks for speed). Run `cihub docs audit` directly for full validation.

### K. Generated References Expansion

- Extend `cihub docs generate` / `cihub docs check` to cover:
 - `docs/reference/TOOLS.md` generated from `cihub/tools/registry.py`
 - `docs/reference/WORKFLOWS.md` generated from `.github/workflows/*.yml` (triggers + inputs table)
- `docs/guides/WORKFLOWS.md` stays narrative-only and links to the generated reference for detailed tables.

### L. ADR Metadata Lint + Index Automation

- Reuse CLI output (e.g., `cihub adr list --json`) to regenerate `docs/adr/README.md` so there is only one source of truth.
- Lint for required metadata (phased in warn → fail):
 - `Status: accepted|proposed|superseded`
 - `Date: YYYY-MM-DD`
 - Optional `Superseded-by: ADR-xxxx`
 - Optional `Implementation:` note pointing to relevant code/services
- Add these checks to `cihub docs audit` so ADR coverage rides the same automation.

### M. Doc Inventory + Counts

- `docs/development/status/STATUS.md` currently lists counts that drift. Decide between:
 1. Drop counts entirely (preferred to avoid churn), or
 2. Auto-generate counts via `cihub docs audit --inventory --json` and surface them in STATUS.md
- Capture the decision in this plan; until then, note that counts are informational and may be removed.

### N. Plain-Text Reference Scan

- Add regex scanning for `docs/...` strings (not just Markdown links) so missing/moved paths are caught even when referenced in prose, scripts, or ADRs.
- Required before we retire legacy stubs (e.g., `docs/development/execution/`); the scan becomes part of `cihub docs audit`.

### O. Doc-Automation Artifacts

- Both `cihub docs stale` and `cihub docs audit` must emit structured outputs under `.cihub/tool-outputs/`:
 - `docs_stale.json`, `docs_stale.prompt.md`, optional `docs_stale.patch`
 - `docs_audit.json` (lifecycle + reference findings)
- Triage bundles (`cihub triage`) can then include these artifacts (category `docs`) for CI visibility.

### P. LLM Readiness Inputs

- For reliable LLM handoff:
 - Produce a doc manifest (`docs_manifest.json`) with path, category (guide/reference/active/archived), generated/manual flag, last-reviewed date
 - Include the stale-reference report (symbol-level, line context) and a diff summary snippet in `docs_stale.json`
 - `cihub docs stale --ai` should bundle manifest + stale report + diff summary into the prompt pack so downstream tools have deterministic context

### Q. Universal Doc Header Template (Manual Docs)

- Manual docs adopt a lightweight header block (generated docs keep their “Generated by …” banner):
 ```
 Status: active | archived | reference
 Owner: <team or person>
 Source-of-truth: CLI | schema | workflow | manual
 Last-reviewed: YYYY-MM-DD
 Superseded-by: <path or ADR> # optional
 ```
- `cihub docs audit` enforces presence/format; headers provide structured metadata for humans, tooling, and LLMs.

## Part 13: Cross-Document Consistency & Metrics Validation (Audit Addendum 2026-01-06)

This section captures additional gaps discovered during an 8-agent documentation audit on 2026-01-06. These issues extend beyond code-to-doc symbol drift into **cross-document consistency** and **metrics validation**.

### R. Metrics/Counts Drift Detection

**Problem:** Docs embed numeric claims like "11 commands, 80 tests" that become stale.

**Examples found:**
- DEVELOPMENT.md line 337: "11 commands" → Reality: 28 commands
- DEVELOPMENT.md line 169, 338: "80+ tests" → Reality: 2120 tests
- MASTER_PLAN.md line 4: "2104 tests" → Reality: 2120 tests

**Implementation for `cihub docs stale`:**

```python
METRICS_PATTERNS = [
 (r'(\d+)\s*(?:CLI\s+)?commands?', 'command_count'),
 (r'(\d+)\s*tests?', 'test_count'),
 (r'(\d+)\s*ADRs?', 'adr_count'),
 (r'(\d+)\s*(?:doc(?:ument)?s?|files?)', 'doc_count'),
]

def get_actual_metrics() -> dict[str, int]:
 """Get current metrics from authoritative sources."""
 return {
 'command_count': _count_cli_commands(), # from cihub --help
 'test_count': _count_pytest_tests(), # from pytest --collect-only
 'adr_count': len(list(Path('docs/adr').glob('0*.md'))),
 'doc_count': len(list(Path('docs').rglob('*.md'))),
 }

def find_stale_metrics(doc_file: Path) -> list[MetricsDrift]:
 """Find numeric claims that don't match reality."""
 actual = get_actual_metrics()
 stale = []
 for line_num, line in enumerate(doc_file.read_text().splitlines(), 1):
 for pattern, metric_key in METRICS_PATTERNS:
 match = re.search(pattern, line, re.IGNORECASE)
 if match:
 claimed = int(match.group(1))
 actual_val = actual.get(metric_key)
 if actual_val and abs(claimed - actual_val) / actual_val > 0.1: # >10% drift
 stale.append(MetricsDrift(
 file=doc_file, line=line_num,
 claimed=claimed, actual=actual_val,
 metric=metric_key
 ))
 return stale
```

**Thresholds:**
- Warn if drift > 10%
- Error if drift > 50%
- Always flag if claimed count is 0 but actual is non-zero

---

### S. Duplicate Task Detection in Planning Docs

**Problem:** Same task appears multiple times in MASTER_PLAN.md, creating confusion.

**Examples found:**
- `cihub docs stale` appears at lines 63, 123, 395, 418 in MASTER_PLAN.md
- `cihub docs audit` appears at lines 124, 126, 397, 424
- TOOLS.md generation appears at lines 130, 355, 396

**Implementation for `cihub docs audit`:**

```python
def find_duplicate_tasks(planning_docs: list[Path]) -> list[DuplicateTask]:
 """Detect duplicate checklist items across planning docs."""
 all_tasks = []
 for doc in planning_docs:
 for line_num, line in enumerate(doc.read_text().splitlines(), 1):
 # Match checklist items: - [ ] Task or - [x] Task
 match = re.match(r'^[-*]\s*\[([ x])\]\s*(.+)$', line.strip())
 if match:
 status, task_text = match.groups()
 # Normalize: lowercase, strip backticks, collapse whitespace
 normalized = re.sub(r'`[^`]+`', '', task_text.lower())
 normalized = ' '.join(normalized.split())
 all_tasks.append(TaskEntry(
 file=doc, line=line_num,
 text=task_text, normalized=normalized,
 completed=(status == 'x')
 ))

 # Group by normalized text (fuzzy match with 80% similarity)
 duplicates = []
 seen = {}
 for task in all_tasks:
 for existing_norm, existing_entries in seen.items():
 if _similarity(task.normalized, existing_norm) > 0.8:
 duplicates.append(DuplicateTask(
 task=task.text,
 locations=existing_entries + [task]
 ))
 break
 else:
 seen.setdefault(task.normalized, []).append(task)

 return duplicates
```

**Consolidation suggestions:**
- Keep canonical entry in §Quick Wins (for CLI features)
- Remove duplicates from detailed sections
- Add cross-reference: "See §Quick Wins line X"

---

### T. Timestamp Freshness Validation

**Problem:** "Last Updated: YYYY-MM-DD" headers become stale.

**Examples found:**
- MASTER_PLAN.md: "Last Updated: 2026-01-05" but file modified after
- CI_PARITY.md: "Last Verified: 2026-01-05" stale by 1+ day

**Implementation for `cihub docs audit`:**

```python
HEADER_PATTERNS = [
 r'\*\*Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})',
 r'\*\*Last Verified:\*\*\s*(\d{4}-\d{2}-\d{2})',
 r'\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})',
 r'Last-reviewed:\s*(\d{4}-\d{2}-\d{2})',
]

def check_timestamp_freshness(
 doc_file: Path,
 warn_days: int = 7,
 error_days: int = 30,
) -> list[TimestampIssue]:
 """Validate timestamp headers are fresh."""
 issues = []
 content = doc_file.read_text()
 today = date.today()

 for pattern in HEADER_PATTERNS:
 match = re.search(pattern, content)
 if match:
 header_date = date.fromisoformat(match.group(1))
 days_old = (today - header_date).days

 if header_date > today:
 issues.append(TimestampIssue(
 file=doc_file, severity='error',
 message=f"Future date in header: {header_date}"
 ))
 elif days_old > error_days:
 issues.append(TimestampIssue(
 file=doc_file, severity='error',
 message=f"Header date {days_old} days old (> {error_days})"
 ))
 elif days_old > warn_days:
 issues.append(TimestampIssue(
 file=doc_file, severity='warn',
 message=f"Header date {days_old} days old (> {warn_days})"
 ))

 return issues
```

**Configuration:**
- `--warn-stale-days N` (default: 7)
- `--error-stale-days N` (default: 30)
- Skip check for archive/ docs (historical)

---

### U. Checklist vs Reality Consistency

**Problem:** Checklist items marked `[ ]` when work is already done.

**Examples found:**
- CLEAN_CODE.md Part 2.1: "Extract Language Strategies" marked `[ ]` but `cihub/core/languages/` exists
- MASTER_PLAN.md line 335: "Commit CLI helpers" marked `[ ]` but already committed
- MASTER_PLAN.md line 352: "Move legacy docs to archive" marked `[ ]` but done

**Implementation:**

```python
# Map checklist items to verification checks
CHECKLIST_VERIFICATIONS = {
 'extract language strategies': lambda: Path('cihub/core/languages/').exists(),
 'implement cihub docs stale': lambda: 'stale' in _get_cli_subcommands('docs'),
 'implement gatespec registry': lambda: Path('cihub/core/gate_specs.py').exists(),
 'move legacy docs to archive': lambda: _archive_has_superseded_headers(),
 'commit cli helpers': lambda: all(
 Path(f'cihub/commands/{cmd}.py').exists()
 for cmd in ['preflight', 'scaffold', 'smoke']
 ),
}

def verify_checklists(design_docs: list[Path]) -> list[ChecklistMismatch]:
 """Cross-reference checklist items against code reality."""
 mismatches = []
 for doc in design_docs:
 for line_num, line in enumerate(doc.read_text().splitlines(), 1):
 match = re.match(r'^[-*]\s*\[([ ])\]\s*(.+)$', line.strip())
 if match: # Unchecked item
 task_text = match.group(2).lower()
 for pattern, verifier in CHECKLIST_VERIFICATIONS.items():
 if pattern in task_text:
 if verifier():
 mismatches.append(ChecklistMismatch(
 file=doc, line=line_num,
 task=match.group(2),
 issue="Marked incomplete but implementation exists"
 ))
 return mismatches
```

**Report format:**
```
CLEAN_CODE.md:35 - Task "Extract Language Strategies" marked [ ] but:
 [x] cihub/core/languages/ directory exists
 [x] Contains: base.py, python.py, java.py, registry.py
 Suggestion: Mark as [x] or clarify remaining work
```

---

### V. Hardcoded Placeholder Detection

**Problem:** Docs contain hardcoded usernames, paths, or placeholder values.

**Examples found:**
- GETTING_STARTED.md: `jguida941/ci-cd-hub` (personal fork URL)
- INTEGRATION_SMOKE_TEST.md: `jguida941/ci-cd-hub` as hub repo default

**Implementation:**

```python
PLACEHOLDER_PATTERNS = [
 # GitHub usernames in URLs (not matching CODEOWNERS)
 (r'github\.com/([a-zA-Z0-9_-]+)/', 'github_username'),
 # Common placeholder markers
 (r'\b(YOUR_[A-Z_]+|CHANGE_ME_PLACEHOLDER|TODO:|FIXME:|XXX:)\b', 'placeholder_marker'),
 # Hardcoded local paths
 (r'(/<home>/[^/\s]+|/<home>/[^/\s]+|C:\\<User>\\[^\\]+)', 'local_path'),
 # Hardcoded IPs (except localhost)
 (r'\b(?!127\.0\.0\.1)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', 'ip_address'),
]

def find_placeholders(
 doc_file: Path,
 expected_usernames: set[str] | None = None,
) -> list[PlaceholderIssue]:
 """Detect hardcoded placeholders that may need updating."""
 if expected_usernames is None:
 expected_usernames = _get_codeowners_usernames()

 issues = []
 for line_num, line in enumerate(doc_file.read_text().splitlines(), 1):
 for pattern, issue_type in PLACEHOLDER_PATTERNS:
 for match in re.finditer(pattern, line):
 value = match.group(1)
 # Skip if it's an expected value
 if issue_type == 'github_username' and value in expected_usernames:
 continue
 issues.append(PlaceholderIssue(
 file=doc_file, line=line_num,
 value=value, issue_type=issue_type,
 severity='warn', # May be intentional examples
 message=f"Possible placeholder: {value}"
 ))
 return issues
```

**Severity:**
- `warn` for usernames (may be intentional examples)
- `error` for TODO:/FIXME: in non-dev docs
- `warn` for local paths

---

### W. Cross-Document Consistency Validation

**Problem:** Same facts appear differently across multiple docs.

**Examples found:**
- Test count: STATUS.md says "2120", MASTER_PLAN says "2104", DEVELOPMENT.md says "80+"
- ADR count: STATUS.md says "37", adr/README.md lists 44 files
- Command count: DEVELOPMENT.md says "11", reality is "28"
- Docs index: `docs/README.md` active list missing files in `docs/development/active/`

**Implementation for `cihub docs audit`:**

```python
# Define canonical sources for each metric
CANONICAL_SOURCES = {
 'test_count': ('pytest --collect-only', r'(\d+) items?'),
 'command_count': ('cihub --help', lambda output: len(_parse_commands(output))),
 'adr_count': ('glob', lambda: len(list(Path('docs/adr').glob('0*.md')))),
}

# Define docs that claim these metrics
DOCS_WITH_METRICS = {
 'test_count': [
 'docs/development/status/STATUS.md',
 'docs/development/MASTER_PLAN.md',
 'docs/development/DEVELOPMENT.md',
 ],
 'command_count': [
 'docs/development/DEVELOPMENT.md',
 'AGENTS.md',
 ],
 'adr_count': [
 'docs/development/status/STATUS.md',
 'docs/adr/README.md',
 ],
}

# Non-metric consistency checks
DOCS_WITH_LISTS = {
 'active_docs': {
 'source_dir': 'docs/development/active',
 'index_doc': 'docs/README.md',
 'status_doc': 'docs/development/status/STATUS.md',
 },
}

def validate_cross_doc_consistency() -> list[ConsistencyIssue]:
 """Validate same facts appear identically across docs."""
 issues = []

 for metric, doc_paths in DOCS_WITH_METRICS.items():
 canonical = _get_canonical_value(metric)

 for doc_path in doc_paths:
 doc = Path(doc_path)
 if not doc.exists():
 continue

 claimed = _extract_metric_from_doc(doc, metric)
 if claimed and claimed != canonical:
 issues.append(ConsistencyIssue(
 metric=metric,
 file=doc,
 claimed=claimed,
 canonical=canonical,
 message=f"{doc.name} claims {metric}={claimed} but canonical is {canonical}"
 ))

 return issues
```

**Output format:**
```
Cross-Document Consistency Report
=================================
test_count (canonical: 2120 from pytest):
 [x] STATUS.md: 2120 (matches)
 [ ] MASTER_PLAN.md: 2104 (drift: -16)
 [ ] DEVELOPMENT.md: 80 (drift: -2040)

Suggestion: Update MASTER_PLAN.md line 4 and DEVELOPMENT.md lines 169, 337, 338
```

---

### X. CHANGELOG Format Validation

**Problem:** CHANGELOG has formatting issues.

**Examples found:**
- Two 2026-01-05 entries out of chronological order
- Missing section separators between some entries
- Inconsistent capitalization in headers

**Implementation:**

```python
def validate_changelog(changelog_path: Path) -> list[ChangelogIssue]:
 """Validate CHANGELOG format and ordering."""
 issues = []
 content = changelog_path.read_text()

 # Extract date headers
 date_pattern = r'^## (\d{4}-\d{2}-\d{2})'
 dates_found = []
 for line_num, line in enumerate(content.splitlines(), 1):
 match = re.match(date_pattern, line)
 if match:
 dates_found.append((line_num, match.group(1)))

 # Check chronological order (most recent first)
 for i in range(len(dates_found) - 1):
 curr_line, curr_date = dates_found[i]
 next_line, next_date = dates_found[i + 1]
 if curr_date < next_date:
 issues.append(ChangelogIssue(
 line=curr_line,
 severity='error',
 message=f"Out of order: {curr_date} appears before {next_date}"
 ))

 # Check for duplicate dates (may be intentional but flag)
 date_counts = Counter(d for _, d in dates_found)
 for date, count in date_counts.items():
 if count > 1:
 issues.append(ChangelogIssue(
 severity='warn',
 message=f"Date {date} appears {count} times - consider merging"
 ))

 # Check separator consistency
 # ... additional format checks

 return issues
```

**Checks performed:**
- Chronological ordering (most recent first)
- Duplicate date detection
- Section separator presence
- Keep a Changelog format compliance (optional)
- Version number format (if using semantic versioning)

---

### Y. Checklist Reference

> **Note:** All Part 13 items are now consolidated in the **Working Checklists** at the top of this document (Checklist C: Metrics & Consistency). Update items there, not here.

---

### Z. Priority Matrix for Part 13 Features

| Feature | Priority | Effort | Value | Dependency |
|---------|----------|--------|-------|------------|
| Cross-doc consistency (W) | High | Medium | High | None |
| Metrics drift (R) | High | Low | High | CLI introspection |
| Checklist-reality (U) | Medium | Medium | Medium | File system checks |
| Timestamp freshness (T) | Medium | Low | Medium | None |
| Duplicate detection (S) | Medium | Medium | Medium | None |
| CHANGELOG validation (X) | Low | Low | Low | None |
| Placeholder detection (V) | Low | Low | Low | CODEOWNERS parsing |

**Recommended implementation order:**
1. Metrics drift (R) - Quick win, high value
2. Cross-doc consistency (W) - Catches most audit findings
3. Timestamp freshness (T) - Simple, prevents stale headers
4. Checklist-reality (U) - Useful for design doc hygiene
5. Duplicate detection (S) - Helps consolidate MASTER_PLAN
6. CHANGELOG validation (X) - Polish
7. Placeholder detection (V) - Nice-to-have

---

## Sources

- [Git documentation on diff](https://git-scm.com/docs/git-diff)
- [git-md-diff for markdown management](https://github.com/Pryx/git-md-diff)
- [Sphinx AutoAPI for docstring extraction](https://github.com/readthedocs/sphinx-autoapi)
- [Python ast module](https://docs.python.org/3/library/ast.html)
- [docstr-coverage for docstring analysis](https://pypi.org/project/docstr-coverage/)
- [Keep a Changelog](https://keepachangelog.com/) - CHANGELOG format standard
- [8-agent documentation audit](2026-01-06) - Source of Part 13 findings
