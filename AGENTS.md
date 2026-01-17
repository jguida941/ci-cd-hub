# AGENTS.md - CI/CD Hub

## Start Here

**Current Priority:** TEST_REORGANIZATION Phase 0 readiness (wizard/CLI validation complete; repo run blockers resolved; matrix green)

| Quick Links | Purpose |
|----------------------------------------------------------------------|--------------------------------------------|
| [MASTER_PLAN.md](docs/development/MASTER_PLAN.md) | Canonical plan, priority order, v1.0 scope |
| [TEST_REORGANIZATION.md](docs/development/active/TEST_REORGANIZATION.md) | Current work - test suite restructuring |
| [DESIGN_JOURNEY.md](docs/development/architecture/DESIGN_JOURNEY.md) | Why decisions were made (context) |

**Next task:** Start Phase 0 file mapping (all 78 files → new homes), then split large monolithic test files

## Architecture Contract (Read First)

- CLI is the product and headless API; command names are stable endpoints.
- TypeScript GUI/CLI consumes `cihub --json`; no direct YAML edits.
- Wizard is a UX layer over the same command handlers + schema (no parallel logic).
- Schema is the config contract; changes require ADR + tests + regenerated docs.
- Workflows are thin wrappers that only call `cihub ...`; no business logic in YAML.
- ADR required for any architectural, CLI-surface, workflow-contract, or schema-default change.
- Packaging defaults (PyPI vs git) must stay aligned across schema, CLI, and docs.

---

## AI Agent Process Guide

> **Follow this process for every task.** This keeps all docs in sync.

### Step 1: Understand Current State

```
1. Read MASTER_PLAN.md → "Active Design Docs - Priority Order" section
2. Check which Priority (#1-#5) is current
3. Read that doc's Master Checklist to find incomplete tasks
```

### Step 2: Before Making Changes

```
1. Check the current priority doc (currently TEST_REORGANIZATION.md)
2. Find the specific Part/Phase you're working on
3. Read any related code files
4. Understand what "done" looks like for that task
```

### Step 3: After EVERY Code Change

```
1. Update the Master Checklist in the priority doc (mark items [x])
2. Update MASTER_PLAN.md if scope/status changed
3. Update AGENTS.md "Current Focus" if priorities shifted
4. Run tests to verify nothing broke
```

### Step 4: After Completing a Phase/Part

```
1. Mark the Phase/Part complete in the doc's Master Checklist
2. Update MASTER_PLAN.md "Active Design Docs - Priority Order" status
3. Update AGENTS.md remaining tasks list
4. Check if next priority doc can now start
```

### Quick Reference: Doc Update Locations

| When you... | Update these docs |
|--------------------------------|--------------------------------------------------------------------|
| Complete a TEST_REORGANIZATION.md task | TEST_REORGANIZATION.md checklist → AGENTS.md tasks → MASTER_PLAN.md status |
| Finish a priority doc entirely | All 5 active docs (shift priorities) → AGENTS.md → MASTER_PLAN.md |
| Change CLI command behavior | AGENTS.md "Commands" → regenerate CLI.md → MASTER_PLAN.md if new |
| Add new design decision | MASTER_PLAN.md "Current Decisions" → AGENTS.md if affects workflow |
| Discover a blocker | Priority doc → MASTER_PLAN.md blockers → AGENTS.md if critical |

### Update Triggers (Keep AGENTS.md in sync)

- CLI surface or output changes (new flags, defaults, JSON schema)
- Config schema/defaults changes (`cihub/data/schema/`, `cihub/data/config/`)
- Workflow contract changes (inputs/outputs, `config-outputs` mapping)
- Packaging/distribution changes (PyPI vs git)
- ADRs added/superseded that affect workflow or architecture

### The Golden Rule

> **Never finish a task without updating the checklist.** If the checklist doesn't reflect reality, the next AI session will repeat work or skip steps.

---

## CLI-first rule (non-negotiable)

Use "CLI" everywhere in docs and behavior descriptions.

- The CLI is the product and the single source of truth. Workflows are thin wrappers.
- If GitHub Actions fails, we do NOT “fix YAML as the solution.”
 - An emergency YAML patch is allowed only to unblock CI.
 - Any stopgap YAML change MUST be absorbed into the CLI immediately.
 - The CLI fix MUST be locked with regression tests so we never hand-edit YAML again.

## First-line workflow (CLI-driven)

- Start with CLI automation before manual edits or workflow changes.
- Run `cihub check` (appropriate tier) as the first-line validation pass.
- For doc changes, run `cihub docs generate`, `cihub docs check`, `cihub docs stale`, and `cihub docs audit` (track gaps in MASTER_PLAN if any command is missing).
- Enable `CIHUB_EMIT_TRIAGE=True` when diagnosing failures and review `.cihub/tool-outputs/` + triage bundles for context.

## Use cihub commands for CI analysis (mandatory)

When investigating CI failures, analyzing workflows, or running tools, **always use cihub commands first**:

### Triage & Analysis Commands
| Task | Command |
|------|---------|
| Check latest failed run | `cihub triage --latest` |
| Analyze specific run | `cihub triage --run ID` |
| Verify tools ran correctly | `cihub triage --verify-tools` |
| Multi-repo triage | `cihub triage --multi --reports-dir DIR` |
| Flaky test detection | `cihub triage --detect-flaky` |
| Gate history analysis | `cihub triage --gate-history` |
| Watch for failures | `cihub triage --watch` |

### Report & Validation Commands
| Task | Command |
|------|---------|
| Validate report structure | `cihub report validate --report PATH` |
| Build report from artifacts | `cihub report build --output-dir DIR` |
| Render summary | `cihub report summary --report PATH` |
| Aggregate hub reports | `cihub report aggregate --output-dir DIR` |
| Generate dashboard | `cihub report dashboard --reports-dir DIR` |

### Python Tool Wrappers (use instead of raw tools)
| Task | Command |
|------|---------|
| Run ruff | `cihub hub-ci ruff --path .` |
| Run black | `cihub hub-ci black --path .` |
| Run bandit | `cihub hub-ci bandit --path .` |
| Run pip-audit | `cihub hub-ci pip-audit` |
| Run mutmut | `cihub hub-ci mutmut --path .` |
| Check pytest results | `cihub hub-ci pytest-summary` |

### Java Tool Wrappers
| Task | Command |
|------|---------|
| Run checkstyle | `cihub hub-ci smoke-java-checkstyle --workdir .` |
| Run spotbugs | `cihub hub-ci smoke-java-spotbugs --workdir .` |
| Run OWASP check | `cihub hub-ci security-owasp --workdir .` |
| Java build | `cihub hub-ci smoke-java-build --workdir .` |
| Java tests | `cihub hub-ci smoke-java-tests --workdir .` |

### Security & Validation Commands
| Task | Command |
|------|---------|
| Run actionlint | `cihub hub-ci actionlint` |
| Run zizmor | `cihub hub-ci zizmor-run` |
| Check gitleaks | `cihub hub-ci gitleaks-summary` |
| License check | `cihub hub-ci license-check` |
| Trivy summary | `cihub hub-ci trivy-summary` |

### Environment & Setup Commands
| Task | Command |
|------|---------|
| Detect language | `cihub detect` |
| Check environment | `cihub preflight` or `cihub doctor` |
| Run local validation | `cihub check` |
| Verify workflow contracts | `cihub verify` |
| Validate config | `cihub validate` |

### Documentation Commands
| Task | Command |
|------|---------|
| Generate docs | `cihub docs generate` |
| Check docs freshness | `cihub docs check` |
| Check broken links | `cihub docs links` |
| Detect stale references | `cihub docs stale` |

### Hub Management Commands
| Task | Command |
|------|---------|
| Validate configs | `cihub hub-ci validate-configs` |
| Validate profiles | `cihub hub-ci validate-profiles` |
| Generate badges | `cihub hub-ci badges` |
| CI summary | `cihub hub-ci summary` |
| Enforce gates | `cihub hub-ci enforce` |

**Why use cihub commands:**
1. Parse artifacts and produce structured JSON output
2. Integrate with triage bundles for context
3. Populate `problems` and `suggestions` in CommandResult
4. Are testable and don't diverge from CLI surface
5. Proves the tools work when used

## Stop-the-line policy

- If a CLI command fails on any repo shape, stop and fix the CLI first.
- No hard-coded special cases for one repo. Fixes must generalize via config, profiles, or detection.

## No hardcoding rule

- Do not add repo-specific hardcoded paths, names, or branching that only works for one repo.
- All behavior must be driven by schema/config booleans, profiles, or detection services.
- If a scenario fails (parent/child POM, monorepo subdir, mixed Java+Python), the fix belongs in CLI/services/core, not in a one-off workflow patch.

## Debugging and failure visibility

- Developer debugging is opt-in via env toggles:
 - CIHUB_DEBUG=True (tracebacks)
 - CIHUB_VERBOSE=True (tool stdout/stderr)
 - CIHUB_DEBUG_CONTEXT=True (decision/context blocks)
 - CIHUB_EMIT_TRIAGE=True (triage bundle)
- When enabled, diagnostics must be rich enough that failures can be fixed by improving CLI logic, not by manual workflow edits.

## Testing is mandatory

- Every CLI command must have a defined contract: args, flags, env toggles, artifacts, exit codes, and failure modes.
- Maintain a single command-contract spec that generates:
 - CLI_COMMAND_AUDIT.md
 - pytest integration tests (parameterized from the same spec)
- CI must validate the CLI across multiple fixture repo shapes. If the CLI does not work across scenarios, refactor until it does.
- Coverage and mutation thresholds are quality gates; changes must keep them green or update thresholds via ADR + config.

## CLI outputs and contracts

- All new or modified CLI commands (including hub-ci subcommands) must support `--json` and return `CommandResult` (existing gaps are tracked in MASTER_PLAN Quick Wins).
- Command modules should not print to stdout/stderr; migrate legacy prints into `cihub/cli.py` rendering or CommandResult payloads when touched.
- CommandResult fields are stable. Update the contract spec + tests when the schema changes.

## Workflow rules

- Workflows must stay minimal. Logic belongs in CLI/services/core.
- Workflows install the CLI from the hub repo (editable when checked out: `pip install -e .`, `pip install -e ".[ci]"`, or `pip install -e "hub[ci]"` for subdir checkouts; reusable workflows may use `pip install "git+https://...@ref"`), then shell out to `cihub ...` only (no composite actions, no inline logic).
- All actions must be pinned (including `harden-runner`).

## Project Overview

CI/CD Hub is a CLI tool and workflow wrapper for running CI across many repos. The CLI is the execution engine; workflows are thin wrappers.

## Shared Config Pipeline (Single Source of Truth)

`cihub/data/schema/ci-hub-config.schema.json`
→ CLI + Wizard (same config model and defaults)
→ `.ci-hub.yml` render
→ `cihub config-outputs` for workflows
→ workflows call `cihub hub-ci ...`

## Source of Truth Hierarchy

1. **Code** (`cihub/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is authoritative CLI documentation.
3. **Schema** (`cihub/data/schema/ci-hub-config.schema.json`) is the config contract.
4. **Plan** (`docs/development/MASTER_PLAN.md`) is the canonical execution plan.

## Current Focus

Live priority order and status live in [MASTER_PLAN.md](docs/development/MASTER_PLAN.md) under
"Active Design Docs - Priority Order." Start there for current work and keep this file stable.
Current focus is resolving repo run blockers (pip install/network + Gradle) after completing wizard/CLI validation, then moving into Test Reorg Phase 0.

### CLI as Headless API (Architecture Principle)

> **CRITICAL:** CLI commands are stable API endpoints. DO NOT restructure command names.

The Python CLI is designed as a **headless API backend** for:
1. **TypeScript GUI/CLI** - maps `/fix-pom` → `cihub fix-pom --json`
2. **PyQt6 GUI** - calls `cihub` via subprocess
3. **GitHub Workflows** - calls `cihub config-outputs`, `cihub hub-ci *`

Changing command names (e.g., `setup-secrets` → `setup secrets`) would break all consumers.
See [MASTER_PLAN.md](docs/development/MASTER_PLAN.md#cli-as-headless-api-architecture-principle) for details.

Follow the active doc's Master Checklist for current tasks (currently TEST_REORGANIZATION.md) after the wizard/CLI validation gate.

---

**v1.0 Quick Wins (after CLEAN_CODE complete):**

**CLI Commands:**
1. [x] `cihub docs stale` - Detect stale code references in docs **DONE** (modularized package, 63 tests)
2. [x] `cihub docs audit` - Doc lifecycle consistency checks **DONE** (39 tests, Part 12.J/L/N/Q + Part 13.R/S/T/U/V/W/X)
3. `cihub config validate` - Validate hub configs
4. `cihub audit` - Umbrella command (docs check + links + adr check + config validate)
5. `--json` flag for all commands including hub-ci subcommands

**Documentation:**
1. [x] Generate `docs/reference/TOOLS.md` from `cihub/tools/registry.py`
2. [x] Generate `docs/reference/WORKFLOWS.md` from `.github/workflows/*.yml`
3. [x] Plain-text reference scan for stale `docs/...` strings **DONE** (via `cihub docs audit`)
4. [x] Universal header enforcement for manual docs **DONE** (via `cihub docs audit` Part 12.Q)
5. [x] `.cihub/tool-outputs/` artifacts for doc automation **DONE** (optional via `--output-dir`)

**Clean Code (many complete):**
1. `_tool_enabled()` consolidation (5 implementations → 1)
2. Gate-spec refactor (26 thresholds wired)
3. Language strategy extraction (Python/Java)
4. Expand CI-engine tests (2 → 151)
5. Output normalization (~7 files remaining)

**Security/CI Hygiene:**
1. Pin `step-security/harden-runner` versions
2. Standardize all action version pins

## Commands

- Test: `make test`
- Lint: `make lint`
- Format: `make format`
- Typecheck: `make typecheck`
- Workflow lint: `make actionlint`
- Generate docs: `python -m cihub docs generate`
- Check docs drift: `python -m cihub docs check`
- Smoke test: `python -m cihub smoke --full`
- Local check (fast): `python -m cihub check`
- Local check (full): `python -m cihub check --full`
- Local check (all): `python -m cihub check --all`
- Contract verify: `python -m cihub verify` (use `--remote` or `--integration` as needed)
- Pre-push verify: `make verify`
- Template sync (check): `python -m cihub sync-templates --check`
- Repo init: `python -m cihub init`
- Detect language: `python -m cihub detect`
- Config tooling: `python -m cihub config ...`
- Single tool run: `python -m cihub run <tool>`
- Report aggregation: `python -m cihub report aggregate`
- Doc freshness: `python -m cihub docs stale` (detects stale code references)
- Doc audit: `python -m cihub docs audit` (lifecycle checks, header enforcement, consistency)
- Doc workflows (planned): `python -m cihub docs workflows` (generate workflow tables)
- Doc manifest (planned): `python -m cihub docs manifest` (doc inventory/metadata)

### Check Tiers

```
cihub check # Fast: lint, format, type, test, actionlint, docs, smoke (~30s)
cihub check --audit # + links, adr, configs (~45s)
cihub check --security # + bandit, pip-audit, trivy, gitleaks (~2min)
cihub check --full # + templates, matrix, license, zizmor (~3min)
cihub check --mutation # + mutmut (~15min)
cihub check --all # Everything
```

Use `--install-missing` to prompt for installing missing optional tools and
`--require-optional` to fail if any are missing.

## Testing Notes

- Run `pytest tests/` for CLI and config changes.
- Do not update test counts in docs unless you ran a verified full test run and can cite it; counts are paused until the owner refreshes them.
- After CLI or schema changes, regenerate reference docs.
- Use `cihub scaffold` + `cihub smoke` for local verification.

## Required After Changes

- CLI or schema changes: `python -m cihub docs generate` and `python -m cihub docs check`.
- Template callers or hub workflow changes: `python -m cihub verify --remote` (requires GH auth) and `pytest tests/test_templates.py`.
- Local validation before push: `make verify` (full checks, contract verify + remote drift, installs missing tools).
- Full integration sweep: `make verify-integration` (clones repos, runs cihub ci; slow, requires GH auth).
- Doc changes: `python -m cihub docs generate`, `python -m cihub docs check`, `python -m cihub docs stale`, and `python -m cihub docs audit`.
- CLI surface changes: regenerate CLI snapshots and update command-contract tests.
- Major CLI changes: re-run hub production workflows.

## Project Structure

- `cihub/` - CLI source and command handlers
- `cihub/data/config/` - Defaults and repo configs
- `cihub/data/schema/` - JSON schema for .ci-hub.yml
- `cihub/data/templates/` - Workflow/templates and scaffold assets
- `cihub/data/templates/legacy/` - Archived dispatch templates (do not use)
- `docs/` - Documentation hierarchy
- `tests/` - pytest suite
- `.github/workflows/` - CI workflows

## Documentation Rules

- Do not duplicate CLI help text in markdown. Generate reference docs from the CLI.
- Do not hand-write config field docs. Generate from schema.
- If code and docs conflict, update docs to match code.
- Generated references are the only source for tables:
 - `docs/reference/CLI.md`, `docs/reference/CONFIG.md` (already)
 - `docs/reference/TOOLS.md` (from `cihub/tools/registry.py`)
 - `docs/reference/WORKFLOWS.md` (from `.github/workflows/*.yml` triggers/inputs)
- Guides stay narrative-only (e.g., `docs/guides/WORKFLOWS.md` links to generated tables).
- Doc lifecycle:
 - In-flight design docs live in `docs/development/active/` and must be listed in `docs/development/status/STATUS.md`.
 - Archive with a “Superseded” header + pointer; update `docs/README.md`, `STATUS.md`, `MASTER_PLAN.md` when paths move.
- Manual docs carry a lightweight header: `Status/Owner/Source-of-truth/Last-reviewed[/Superseded-by]`. Generated docs keep their generated banner.
- ADRs require `Status` and `Date` (plus `Superseded-by` when applicable); ADR index is generated from `cihub adr list`.
- New architecture or cross-surface decisions require a new ADR (or supersede an existing one).
- Doc lifecycle/header enforcement belongs in `cihub docs audit` and runs in `cihub check --audit`.
- `cihub docs check`, `cihub docs stale`, and `cihub docs audit` are required before push for doc changes.

## Doc automation outputs

- `cihub docs stale` emits `docs_stale.json` and `docs_stale.prompt.md` to `.cihub/tool-outputs/` (use `--output-dir`).
- `cihub docs audit` emits `docs_audit.json` to `.cihub/tool-outputs/`.
- Triage bundles (`CIHUB_EMIT_TRIAGE`) must pick up docs tool outputs for visibility when present.

## Scope Rules

### Always

- Update `docs/development/MASTER_PLAN.md` checkboxes when scope changes.
- Update `docs/development/CHANGELOG.md` for user-facing changes.
- Regenerate docs after CLI or schema changes.
- Run doc gates before push when docs change: `cihub docs generate`, `cihub docs check`, `cihub docs stale`, and `cihub docs audit`.

### Ask First

- Modifying `.github/workflows/`.
- Changing `cihub/data/schema/` or `cihub/data/config/repos/`.
- Archiving/moving docs or ADRs.
- Changing CLI command surface or defaults.

### Never

- Delete docs (archive instead).
- Commit secrets or credentials.
- Change workflow pins without explicit approval.
- Write inline scripts in YAML workflows. All logic must be in CLI commands.
 Workflows are thin wrappers that call `cihub <command>` - never embed shell/Python.

### CI Parity Rule

- If `hub-production-ci.yml` fails on something that can be reproduced locally, add it to `cihub check` or document why it's CI-only.
- Run `cihub check --all` before pushing to catch issues early.

### CI Parity Map

> **Full details:** See [docs/development/CI_PARITY.md](docs/development/CI_PARITY.md) for the complete parity map with check tiers.

Quick summary:
- **Exact match:** validate-configs, validate-profiles, validate-templates, verify-matrix-keys
- **Partial match:** actionlint, ruff, mypy, pytest, yamllint, bandit, pip-audit, gitleaks, trivy, zizmor, mutmut, license-check
- **CI-only:** SARIF uploads, reviewdog, dependency-review, scorecard, harden-runner, badge updates
- **Local-only:** docs-check, docs-links, adr-check, preflight, smoke

## Key Architecture

- Entry point workflow is `hub-ci.yml` (wrapper that routes to language-specific workflows).
- Fixtures repo is CI/regression only; local dev uses `cihub scaffold` + `cihub smoke`.
- Generated refs: `docs/reference/CLI.md` and `docs/reference/CONFIG.md` (don't edit by hand).
- Doc automation/LLM:
 - `cihub docs stale` emits `docs_stale.json` and `docs_stale.prompt.md` to `.cihub/tool-outputs/` (use `--output-dir`).
 - `cihub docs audit` emits `docs_audit.json` to `.cihub/tool-outputs/`.
 - Triage bundles (`CIHUB_EMIT_TRIAGE=True`) should pick up these artifacts when present (category `docs`).
- CLI output contract (target): all commands should support `--json` and return `CommandResult`; `cli.py` should be the only place that prints. **Current gaps:** hub-ci subcommands return `int` and print directly-see v1.0 Quick Wins for migration plan.

## Report Field Semantics

The CI report (`report.json`) uses three distinct boolean maps to track tool execution:

| Field | Meaning | Example |
|--------------------|----------------------------|------------------------------------------------|
| `tools_configured` | Tool was enabled in config | `"ruff": true` means ruff is configured to run |
| `tools_ran` | Tool actually executed | `"ruff": true` means ruff command was invoked |
| `tools_success` | Tool ran AND passed | `"ruff": true` means ruff found no lint errors |

### Key distinctions

1. **`tools_ran` vs `tools_success`**: A tool can run but fail. For example, `ruff` may execute (`tools_ran.ruff=true`) but find errors (`tools_success.ruff=false`).

2. **`tools_configured` vs `tools_ran`**: A tool can be configured but not run (skipped due to missing files, disabled by flag, etc.). Validator warns on this "drift."

3. **Verification hierarchy** (for triage/validation):
 - Primary: Check `tool_metrics` for actual counts (e.g., `ruff_errors`, `bandit_high`)
 - Secondary: Check artifacts exist in `.cihub/tool-outputs/`
 - Fallback: Trust `tools_success` value if metrics/artifacts unavailable

### Validation warnings

The report validator detects these issues:
- **DRIFT**: `tools_configured.X=true` but `tools_ran.X=false` (tool should have run but didn't)
- **No proof**: `tools_ran.X=true` + `tools_success.X=true` but no metrics/artifacts found
- **Threshold incomplete**: Missing `coverage_min` or `mutation_score_min` in thresholds (renders as "-" in summary)
- **Threshold sanity**: Permissive security thresholds (`max_critical_vulns > 0`) trigger warnings

## Threshold Strategy by Repo Type

The hub uses different threshold profiles for different repo purposes:

| Repo Type | Coverage | Mutation | Critical | High | Purpose |
|----------------------------------|----------|----------|----------|------|--------------------------------|
| **Production** (defaults) | 70% | 70% | 0 | 0 | Strict quality standards |
| **Canary** (`canary-*.yaml`) | 70% | 70% | 0 | 0 | Test real production failures |
| **Fixtures** (`fixtures-*.yaml`) | 50% | 0% | 100 | 100 | Always-pass CI mechanics tests |
| **Hub CI** (`hub_ci`) | 70% | 70% | 0 | 0 | Strict for hub itself |

### Rationale

- **Canary repos**: Use production thresholds to catch real regressions in template sync and workflows
- **Fixture repos**: Use permissive thresholds to test CI *mechanics*, not code quality
 - Fixture thresholds intentionally trigger sanity warnings (expected behavior)
 - These repos validate that tools run, artifacts generate, and reports parse correctly
- **Production repos**: Use strict thresholds to enforce quality standards

### Customizing Thresholds

Override in `cihub/data/config/repos/<repo>.yaml`:
```yaml
thresholds:
 coverage_min: 80 # Higher than default
 mutation_score_min: 60 # Lower for slow codebases
 max_critical_vulns: 0 # Never allow critical vulns
 max_high_vulns: 2 # Allow some high vulns (legacy code)
```

Per-tool settings override global thresholds:
```yaml
python:
 tools:
 pytest:
 min_coverage: 85 # Overrides thresholds.coverage_min
```

## Key Files

- `cihub/cli.py` (CLI entry point - thin adapter)
- `cihub/data/schema/ci-hub-config.schema.json` (config contract)
- `cihub/data/config/defaults.yaml` (defaults)
- `docs/development/MASTER_PLAN.md` (active plan)

---

## Complete Documentation Map

### Planning & Status
| Document | Purpose | When to Read |
|---------------------------------------------------|----------------------------------------|--------------------------------------------|
| [MASTER_PLAN.md](docs/development/MASTER_PLAN.md) | Canonical plan, v1.0 scope, priorities | **First** - understand what we're building |
| [STATUS.md](docs/development/status/STATUS.md) | Current state, recent changes | Check what's done recently |
| [CHANGELOG.md](docs/development/CHANGELOG.md) | User-facing changes history | Before releases |

### Active Design Docs (Priority Order)
| Priority | Document | Purpose |
|----------|------------------------------------------------------------------------------|------------------------------------------------|
| #1 | [CLEAN_CODE.md](docs/development/archive/CLEAN_CODE.md) | Architecture improvements (archived) |
| #2 | [SYSTEM_INTEGRATION_PLAN.md](docs/development/archive/SYSTEM_INTEGRATION_PLAN.md) | Registry/wizard/schema integration (archived) |
| #3 | [TEST_REORGANIZATION.md](docs/development/active/TEST_REORGANIZATION.md) | Test suite restructuring |
| #4 | [DOC_AUTOMATION_AUDIT.md](docs/development/active/DOC_AUTOMATION_AUDIT.md) | Doc freshness automation |
| #5 | [TYPESCRIPT_CLI_DESIGN.md](docs/development/active/TYPESCRIPT_CLI_DESIGN.md) | Interactive TypeScript CLI |
| #6 | [PYQT_PLAN.md](docs/development/active/PYQT_PLAN.md) | Desktop GUI wrapper |

### Architecture & History
| Document | Purpose |
|----------------------------------------------------------------------|------------------------------------|
| [DESIGN_JOURNEY.md](docs/development/architecture/DESIGN_JOURNEY.md) | Why decisions were made, evolution |
| [ARCH_OVERVIEW.md](docs/development/architecture/ARCH_OVERVIEW.md) | Current architecture overview |
| [CI_PARITY.md](docs/development/CI_PARITY.md) | Local vs CI tool mapping |

### Reference (Generated - Don't Edit)
| Document | Generated From |
|---------------------------------------|-----------------------|
| [CLI.md](docs/reference/CLI.md) | `cihub docs generate` |
| [CONFIG.md](docs/reference/CONFIG.md) | `cihub docs generate` |

---

## Code Architecture

### Module Structure
```
cihub/
├── cli.py # Entry point - thin adapter, NO business logic
├── cli_parsers/ # Argparse setup (split by command group)
├── commands/ # Command handlers (return CommandResult)
│ ├── hub_ci/ # hub-ci subcommands (48 functions)
│ └── report/ # report subcommands
├── core/ # Business logic
│ ├── languages/ # Language strategies (Python/Java)
│ ├── ci_runner/ # Tool execution
│ └── gate_specs.py # Threshold definitions
├── services/ # Service layer (GUI-ready)
│ ├── triage/ # Triage bundle generation
│ └── configuration.py # Config loading facade
├── config/ # Config loading internals
├── output/ # OutputRenderer (JSON/Human)
├── types.py # CommandResult dataclass
└── utils/ # Shared utilities
```

### Key Patterns

**1. CommandResult Pattern** (all commands must use):
```python
from cihub.types import CommandResult

def cmd_example(args) -> CommandResult:
 # Do work...
 return CommandResult(
 exit_code=0,
 summary="Operation completed",
 data={"key": "value"}, # Structured data
 problems=[], # Issues found
 suggestions=[], # Recommendations
 )
```

**2. Language Strategy Pattern**:
```python
from cihub.core.languages import get_strategy

strategy = get_strategy("python") # or "java"
tools = strategy.get_default_tools()
result = strategy.run_tools(config, context)
```

**3. Lazy Import Pattern** (in cli.py):
```pythonnd 
def cmd_detect(args):
 from cihub.commands.detect import cmd_detect as handler
 return handler(args) # Import only when command is called
```

---

## Common Tasks - How To

### Migrate print() to CommandResult
```python
# BEFORE (bad):
def cmd_foo(args):
 print("Starting...")
 result = do_work()
 print(f"Found {len(result)} items")
 return 0

# AFTER (good):
def cmd_foo(args) -> CommandResult:
 result = do_work()
 return CommandResult(
 exit_code=0,
 summary=f"Found {len(result)} items",
 data={"items": result, "count": len(result)},
 )
```

### Add a New CLI Command
1. Create handler in `cihub/commands/new_cmd.py`
2. Add parser in `cihub/cli_parsers/` (appropriate group)
3. Register in `cihub/cli_parsers/registry.py`
4. Add wrapper in `cihub/cli.py`
5. Add to `CommandHandlers` dataclass
6. Write tests in `tests/test_commands_*.py`
7. Run `cihub docs generate` to update CLI.md

### Debug a Failing Command
```bash
CIHUB_DEBUG=True CIHUB_VERBOSE=True python -m cihub <command>
# Or for full triage:
CIHUB_EMIT_TRIAGE=True python -m cihub <command>
# Check .cihub/tool-outputs/ for artifacts
```

---

## Session Handoff Checklist

Before ending a session, ensure:

- [ ] All modified files are saved
- [ ] Checklists updated in priority doc (TEST_REORGANIZATION.md)
- [ ] AGENTS.md "Next task" updated if changed
- [ ] Tests pass (`make test`)
- [ ] Summary provided of what was done

**Handoff format:**
```
## Session Summary
- **Completed:** [list of completed tasks]
- **Files modified:** [list of files]
- **Next task:** [specific next step]
- **Blockers:** [any blockers discovered]
```

---

## Critical Constraints

1. **CLI commands are API endpoints** - never restructure names
2. **No print() in commands** - use CommandResult
3. **No logic in workflows** - CLI is the engine
4. **Schema is source of truth** for config
5. **Always update checklists** after completing tasks
