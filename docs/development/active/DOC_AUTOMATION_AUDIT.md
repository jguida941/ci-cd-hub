# Documentation Automation Audit & Design

**Date:** 2026-01-04
**Last Updated:** 2026-01-05 (Implementation status audit)
**Problem:** Manual documentation updates take 4+ hours/day. With 50+ docs and 28,000 lines, keeping them in sync with code changes is unsustainable.

---

## Implementation Status (2026-01-05)

| Component | Status | Notes |
|-----------|--------|-------|
| `cihub docs generate` | ✅ **IMPLEMENTED** | Generates CLI.md, CONFIG.md |
| `cihub docs check` | ✅ **IMPLEMENTED** | Drift detection for generated docs |
| `cihub docs links` | ✅ **IMPLEMENTED** | Internal link validation |
| `cihub docs stale` | ❌ **NOT IMPLEMENTED** | Core feature — see Part 9 for design |
| `cihub docs audit` | ❌ **NOT IMPLEMENTED** | Lifecycle enforcement — see Part 12 |
| `.cihub/tool-outputs/` for docs | ❌ **NOT IMPLEMENTED** | No docs artifacts generated yet |
| AI prompt pack output | ❌ **NOT IMPLEMENTED** | Design ready in Part 12.D |

**Overall:** ~30% implemented. Core `docs stale` MVP estimated at 2-3 days; full spec is larger.

**Priority Recommendation:** Start with `docs stale` MVP (Python AST + backtick extraction + git range), then expand.

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

---

## Working Checklists (For Humans + AI)

### Checklist A: Implementation Milestones (CIHub)

- [ ] Implement `cihub docs stale` baseline comparisons (base vs head) for:
  - [ ] Python AST symbols
  - [ ] Schema key paths
  - [ ] CLI surface drift (help snapshot)
  - [ ] File move/delete detection (`--name-status --find-renames`)
- [ ] Emit CIHub-style artifacts (optional but recommended):
  - [ ] `.cihub/tool-outputs/docs_stale.json`
  - [ ] `.cihub/tool-outputs/docs_stale.prompt.md`
  - [ ] `.cihub/tool-outputs/docs_stale.stdout.log` / `.stderr.log` (if applicable)
- [ ] Add `cihub check --audit` integration (after trust is established)
- [ ] Add snapshots/regression coverage:
  - [ ] JSON snapshot (syrupy)
  - [ ] AI prompt pack snapshot (syrupy)
  - [ ] Git-range matrix tests (merge-base, rename/move/delete)
  - [ ] Hypothesis markdown fuzz/property tests
  - [ ] Perf benchmark budget on ~28k doc lines

### Checklist B: AI Prompt Pack “Do Not Break These” Rules

When using `docs stale --ai` output (or a future `cihub docs update --llm-runner ...`):
- [ ] Do not edit generated docs under `docs/reference/**` (use `cihub docs generate/check` instead)
- [ ] Do not modify ADR content (ADRs require human authorship)
- [ ] Prefer minimal edits: change only stale tokens/commands/flags/paths
- [ ] Preserve code fences and formatting (especially CLI examples)
- [ ] Use “CLI” terminology (never internal nicknames)
- [ ] Produce a patch/diff output for review; do not auto-apply by default

---

## Part 1: Current Documentation Inventory

### By Category

| Category                | Files | Lines  | Can Auto-Generate?                           |
|-------------------------|-------|--------|----------------------------------------------|
| ADRs                    | 37    | ~3,700 | ❌ No (architectural decisions require human) |
| Reference (CLI, Config) | 3     | ~2,600 | ✅ Yes (your `cihub docs generate` does this) |
| Guides                  | 8     | ~2,300 | ⚠️ Partially (examples can be validated)     |
| Development/Status      | 10+   | ~3,500 | ⚠️ Partially (status can track code)         |
| Archive                 | 15+   | ~5,000 | ❌ No (historical, shouldn't change)          |
| Research                | 1     | ~1,600 | ❌ No (notes, not synced to code)             |

### Total: ~28,000 lines across 70+ files

---

## Part 2: How Your Current Automation Works

### 1. `cihub docs generate` (works well ✅)

**Location:** `cihub/commands/docs.py`

**How it works:**
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ argparse parser │────▶│ _render_parser() │────▶│ CLI.md      │
└─────────────────┘     └──────────────────┘     └─────────────┘

┌─────────────────────────┐     ┌────────────────────┐     ┌─────────────┐
│ schema/ci-hub-config.   │────▶│ _schema_entries()  │────▶│ CONFIG.md   │
│ schema.json             │     └────────────────────┘     └─────────────┘
└─────────────────────────┘
```

**Key insight:** This works because it extracts from **structured sources** (argparse, JSON schema). The schema defines the shape; the generator reads it and outputs markdown.

### 2. `cihub adr new` (works well ✅)

**Location:** `cihub/commands/adr.py`

**How it works:**
- `_get_next_number()` scans existing files for the highest ADR number
- Creates from hardcoded template with auto-filled date
- Updates `docs/adr/README.md` index automatically

**Limitation:** The *content* of ADRs must be written by humans. The decision, context, and consequences are architectural judgment—no tool can generate those.

### 3. `cihub docs check` (detects drift ✅)

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
│                        DOC FRESHNESS PIPELINE                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. EXTRACT         2. INDEX           3. DIFF        4. ALERT   │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  ┌─────────┐       ┌─────────────┐    ┌─────────┐   ┌─────────┐  │
│  │ Code    │──────▶│ References  │───▶│ Compare │──▶│ Stale   │  │
│  │ Symbols │       │ Index       │    │ to Git  │   │ Report  │  │
│  └─────────┘       └─────────────┘    │ Diff    │   └─────────┘  │
│       │                  ▲            └─────────┘        │       │
│       │                  │                               ▼       │
│  ┌─────────┐       ┌─────────────┐              ┌─────────────┐  │
│  │ Docs    │──────▶│ Doc         │              │ AI Update   │  │
│  │ (.md)   │       │ References  │              │ (Optional)  │  │
│  └─────────┘       └─────────────┘              └─────────────┘  │
│                                                                  │
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
- File paths: `cihub/commands/docs.py`

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
1. ✅ Run `cihub docs check` in CI (already possible)
2. ✅ Run `cihub docs generate` before commits

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
| Docs generate/check | `cihub/commands/docs.py` |
| ADR management | `cihub/commands/adr.py` |
| Schema | `schema/ci-hub-config.schema.json` |
| CLI parser | `cihub/cli_parsers/` |
| Exit codes | `cihub/exit_codes.py` |

---

---

## Part 9: Finalized Implementation (`cihub docs stale`)

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
│                    cihub docs stale                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. EXTRACT SYMBOLS          2. EXTRACT DOC REFS            │
│  ────────────────────       ────────────────────            │
│  cihub/**/*.py              docs/**/*.md                    │
│       │                           │                          │
│       ▼                           ▼                          │
│  ast.parse()                 regex backticks                │
│  - functions                 - `symbol_name`                │
│  - classes                   - skip code blocks             │
│  - constants                 - skip archive/                │
│       │                           │                          │
│       ▼                           ▼                          │
│  {name: CodeSymbol}          [DocReference]                 │
│                                                              │
│  3. GIT DIFF                 4. CORRELATE                   │
│  ────────────────────       ────────────────────            │
│  git diff --since           match refs to changes           │
│  git diff --name-status     detect moved/deleted files      │
│       │                           │                          │
│       ▼                           ▼                          │
│  changed_symbols             stale_references               │
│  moved_deleted_files                                        │
│                                                              │
│  5. OUTPUT                                                   │
│  ────────────────────                                       │
│  --json  → CommandResult.data                               │
│  --ai    → Markdown prompt for LLM                          │
│  default → Human-readable summary                           │
│                                                              │
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
| `tests/test_docs_stale.py` | **CREATE** - tests |

### User Decisions (Confirmed)

1. **AI Output:** Stdout (pipe to file: `cihub docs stale --ai > report.md`)
2. **Skip archive:** Yes by default, `--all` flag includes everything
3. **Git range:** Flexible `--since` flag supports both `HEAD~N` and `origin/main..HEAD`
4. **File detection:** Yes - detect both symbol changes AND moved/deleted file references

---

## Part 10: Testing Strategy

### Principle: Test in Isolation First

We will NOT touch any real docs until the tool is proven to work.

### Phase 1: Unit Tests (`tests/test_docs_stale.py`)

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
│   ├── module_a.py      # Has: def old_function(), class OldClass
│   └── module_b.py      # Has: def stable_function()
├── docs/
│   ├── guide.md         # References: `old_function`, `stable_function`
│   └── readme.md        # References: `OldClass`, `module_a.py`
└── .git/                # Fake git history
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

1. ✅ Unit tests pass for all extraction functions
2. ✅ Integration test catches known stale references
3. ✅ Manual smoke test works in isolated directory
4. ✅ Dry run on real codebase produces sensible output
5. ✅ No false positives for common patterns (e.g., `true`, `false`, file extensions)

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
  cihub scaffold python-pyproject /tmp/test  # This could be stale
  ```
- CLI examples are almost always in bash/shell fences
- Python code examples in fences (like the pseudocode in Part 4) should be skipped - they're illustrative, not executable

**Implementation:**
```python
# Parse these fence types for CLI references:
PARSED_FENCE_TYPES = {"bash", "shell", "console", "sh", "zsh", ""}  # "" = untagged fences

# Skip these fence types entirely:
SKIPPED_FENCE_TYPES = {"python", "json", "yaml", "xml", "java", ...}
```

**Flag:** `--skip-fences` to disable fence parsing entirely (for edge cases)

---

#### Decision 2: Generated Docs Exclusion

**Decision:** Exclude `docs/reference/` by default. Include root `README.md`.

**Rationale:**
- `docs/reference/` contains CLI.md, CONFIG.md, TOOLS.md - all auto-generated by `cihub docs generate`
- These are already checked by `cihub docs check` which compares against regenerated content
- Running staleness check on generated docs is circular - they're BY DEFINITION current (regenerated from source)
- Root `README.md` is handwritten and references code symbols - it CAN become stale

**Implementation:**
```python
DEFAULT_EXCLUDE_PATTERNS = [
    "docs/reference/**",  # Generated docs - use `cihub docs check` instead
    "docs/development/archive/**",  # Archived docs - historical, shouldn't change
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
| `tests/test_docs_stale.py` | **CREATE** | Comprehensive tests per above |
| `tests/snapshots/cli_help.txt` | MODIFY | Regenerate after CLI changes |

### Finalized CLI Surface

```bash
# Complete flag set
cihub docs stale [OPTIONS]

Options:
  --since REF           Git revision range (default: HEAD~10)
  --all                 Include archived docs (docs/development/archive/)
  --include-generated   Include generated docs (docs/reference/) - rarely needed
  --json                JSON output for scripts/CI
  --ai                  AI-consumable markdown output (no network calls)
  --fail-on-stale       Exit non-zero if stale refs found (for CI)
  --code PATH           Code directory (default: cihub/)
  --docs PATH           Docs directory (default: docs/)
  --skip-fences         Skip bash/shell code fences (default: parse them)
  --output-dir DIR      Optional output dir for CIHub-style artifacts (e.g., .cihub/)
  --tool-output PATH    Optional path to write tool-style JSON (for triage/tool-outputs)
  --ai-output PATH      Optional path to write the AI prompt pack (markdown)
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

1. ✅ **Architectural decisions finalized** (Part 11)
2. ⬜ **Create `cihub/commands/docs_stale.py`** with:
   - Symbol extraction (AST-based, classifies added/removed/renamed)
   - Reference extraction (backticks + bash fences + file paths)
   - Baseline compare (base vs head) via `git show` for code/schemas/CLI surface + file move/delete detection
   - Correlation logic (only flag REMOVED/RENAMED, not ADDED)
   - Three output modes (human, JSON, AI markdown)
3. ⬜ **Wire CLI** - Update `cli_parsers/docs.py`, `cli_parsers/types.py`, `cli.py`
4. ⬜ **Create tests** - `tests/test_docs_stale.py` with unit + integration tests
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
  - Schema: load `schema/ci-hub-config.schema.json` at base and head and diff key paths (reuse schema traversal approach from `cihub/commands/docs.py`)
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
- **Integration:** run automatically inside `cihub check --audit` so local runs and CI share the same gate.

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
  Superseded-by: <path or ADR>  # optional
  ```
- `cihub docs audit` enforces presence/format; headers provide structured metadata for humans, tooling, and LLMs.

## Sources

- [Git documentation on diff](https://git-scm.com/docs/git-diff)
- [git-md-diff for markdown management](https://github.com/Pryx/git-md-diff)
- [Sphinx AutoAPI for docstring extraction](https://github.com/readthedocs/sphinx-autoapi)
- [Python ast module](https://docs.python.org/3/library/ast.html)
- [docstr-coverage for docstring analysis](https://pypi.org/project/docstr-coverage/)
