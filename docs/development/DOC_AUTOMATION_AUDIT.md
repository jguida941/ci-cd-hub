# Documentation Automation Audit & Design

**Date:** 2026-01-04
**Problem:** Manual documentation updates take 4+ hours/day. With 50+ docs and 28,000 lines, keeping them in sync with code changes is unsustainable.

---

## Part 1: Current Documentation Inventory

### By Category

| Category | Files | Lines | Can Auto-Generate? |
|----------|-------|-------|-------------------|
| ADRs | 37 | ~3,700 | ❌ No (architectural decisions require human) |
| Reference (CLI, Config) | 3 | ~2,600 | ✅ Yes (your `cihub docs generate` does this) |
| Guides | 8 | ~2,300 | ⚠️ Partially (examples can be validated) |
| Development/Status | 10+ | ~3,500 | ⚠️ Partially (status can track code) |
| Archive | 15+ | ~5,000 | ❌ No (historical, shouldn't change) |
| Research | 1 | ~1,600 | ❌ No (notes, not synced to code) |

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
│                        DOC FRESHNESS PIPELINE                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. EXTRACT         2. INDEX           3. DIFF        4. ALERT   │
│  ─────────────────────────────────────────────────────────────   │
│                                                                   │
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
│                                                                   │
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

## Sources

- [Git documentation on diff](https://git-scm.com/docs/git-diff)
- [git-md-diff for markdown management](https://github.com/Pryx/git-md-diff)
- [Sphinx AutoAPI for docstring extraction](https://github.com/readthedocs/sphinx-autoapi)
- [Python ast module](https://docs.python.org/3/library/ast.html)
- [docstr-coverage for docstring analysis](https://pypi.org/project/docstr-coverage/)