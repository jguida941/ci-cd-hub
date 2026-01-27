# CI/CD Hub - Master Plan

**Status:** active  
**Owner:** Development Team  
**Source-of-truth:** manual   
**Last-reviewed:** 2026-01-26  
**Last Updated:** 2026-01-26 (Real-repo audit batch running; OWASP multi-module aggregate fix added)  

> This is THE plan. All action items live here. STATUS.md tracks current state.

---

## AI CI Loop Proposal (Active Design Doc)

See [AI_CI_LOOP_PROPOSAL.md](docs/development/active/AI_CI_LOOP_PROPOSAL.md). This is a draft internal initiative now tracked in the active priority list.

**Status update:** CLI_WIZARD_SYNC_AUDIT archived; TEST_REORGANIZATION + DOC_AUTOMATION_AUDIT archived.
**Current focus:** TYPESCRIPT_CLI_DESIGN Phase 8 (AI Enhancement), tool audit execution, and architecture audit.

---

## CURRENT PRIORITY AT A GLANCE

> Current priority is **#6** (first non-archived doc). TYPESCRIPT_CLI_DESIGN in progress (Phase 8).

| Priority | Document                                                                          | Status   | Next Action                                      |
|----------|-----------------------------------------------------------------------------------|----------|--------------------------------------------------|
| **#1 **  | CLEAN_CODE.md                                                                     | ARCHIVED | Complete (archived)                              |
| **#2 **  | [SYSTEM_INTEGRATION_PLAN.md](docs/development/archive/SYSTEM_INTEGRATION_PLAN.md) | ARCHIVED | Complete (archived)                              |
| **#3 **  | [TEST_REORGANIZATION.md](docs/development/archive/TEST_REORGANIZATION.md)         | ARCHIVED | Complete (Phase 4 property tests + Phase 5 docs) |
| **#4 **  | [DOC_AUTOMATION_AUDIT.md](docs/development/archive/DOC_AUTOMATION_AUDIT.md)        | ARCHIVED | Complete (archived)                              |
| **#5 **  | CLI_WIZARD_SYNC_AUDIT.md                                                          | Archived | Phase 5 cleanup complete (archived 2026-01-19)  |
| **#6 **  | TYPESCRIPT_CLI_DESIGN.md                                                          | In Progress | Execute tool audit per `TOOL_TEST_AUDIT_PLAN.md` |
| **#7 **  | AI_CI_LOOP_PROPOSAL.md                                                            | Draft    | Define scope and sequencing                      |
| **#8 **  | PYQT_PLAN.md                                                                      | DEFERRED | Wait for TypeScript CLI                          |

---

## Purpose

Single source of truth for **priorities, scope, and sequencing**. Individual planning docs own the **detailed implementation plans**.

## Multi-Agent Coordination (Production)

MASTER_PLAN is the canonical coordination point. All agents must read this file and [AGENTS.md](../../AGENTS.md) before starting work.

### Parallel Workstreams (Internal)

| Workstream          | Source Doc                                | Checklist Location              | Notes                                                 |
|---------------------|-------------------------------------------|---------------------------------|-------------------------------------------------------|
| Remediation Plan    | `docs/development/archive/remediation.md` | Remediation phases and findings | Archived intake log; follow-ups tracked in BACKLOG.md |

### Agent Assignment (Operational)

Use this table to keep parallel agents in scope and avoid overlapping edits.

| Agent                          | Scope                                 | Primary Docs                                      | Notes                                   |
|--------------------------------|---------------------------------------|---------------------------------------------------|-----------------------------------------|
| Coordinator                    | Orchestrate scopes, resolve conflicts | `docs/development/MASTER_PLAN.md`, `AGENTS.md`    | Owns file ownership map                 |
| Remediation Phase 1 (Code)     | R-001/R-002 fixes + tests             | `docs/development/archive/remediation.md`         | Archived (complete)                     |
| Remediation Phase 2 (Docs/ADR) | R-012/R-024/R-023 alignment           | `docs/development/archive/remediation.md`         | Archived (complete)                     |
| CI Stabilization               | R-033 triage/parser + snapshot drift  | `docs/development/archive/remediation.md`         | Archived (complete)                     |
| CLEAN_CODE Reconciliation      | Status accuracy cleanup               | `docs/development/archive/CLEAN_CODE.md`          | Archived (complete)                     |
| AI Loop Proposal               | Proposal + internal tooling doc       | `docs/development/active/AI_CI_LOOP_PROPOSAL.md`  | CLI surface + workflow wrapper approved |
| Test Reorg Blockers            | Validate blocker list                 | `docs/development/archive/TEST_REORGANIZATION.md` | Archived (complete)                     |
| Doc Automation Refs            | TOOLS/WORKFLOWS gaps                  | `docs/development/archive/DOC_AUTOMATION_AUDIT.md` | Report only                             |

### File Ownership Map (Authoritative)

> **This table is authoritative.** Agents may only edit files in their "Exclusive Edit" column.
> Read-only access is unrestricted. Conflicts require Coordinator resolution.

| Agent                        | Exclusive Edit Rights                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Read-Only                                 | Notes                                           |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|-------------------------------------------------|
| **Coordinator (0)**          | `docs/development/MASTER_PLAN.md`, `AGENTS.md`, `docs/development/status/STATUS.md`                                                                                                                                                                                                                                                                                                                                                                                                        | All                                       | Updates ownership map, resolves conflicts       |
| **Remediation Code (1)**     | `cihub/commands/setup.py`, `cihub/commands/init.py`, `tests/test_init_override.py`, `tests/test_setup_flow.py`                                                                                                                                                                                                                                                                                                                                                                             | `docs/development/archive/remediation.md` | Archived (no active edits)                      |
| **Remediation Docs (2)**     | `docs/adr/0051-wizard-profile-first-design.md`, `docs/reference/TOOLS.md`                                                                                                                                                                                                                                                                                                                                                                                                                  | `docs/development/archive/remediation.md` | Archived (no active edits)                      |
| **CI Stabilization (3)**     | `cihub/commands/triage_cmd.py`, `tests/test_triage*.py`, snapshot files                                                                                                                                                                                                                                                                                                                                                                                                                    | `docs/development/archive/remediation.md` | Archived (no active edits)                      |
| **CLEAN_CODE Reconcile (4)** | `docs/development/archive/CLEAN_CODE.md` (status sections only)                                                                                                                                                                                                                                                                                                                                                                                                                            | `docs/development/MASTER_PLAN.md`         | Archived (complete)                             |
| **AI Loop Proposal (5)**     | `docs/development/active/AI_CI_LOOP_PROPOSAL.md`, `cihub/commands/ai_loop.py`, `templates/hooks/`, `tests/test_ai_loop.py`, `cihub/commands/ci.py`, `cihub/utils/env_registry.py`, `tests/test_commands_ci.py`, `cihub/services/ai/`, `cihub/cli.py`, `cihub/cli_parsers/core.py`, `cihub/cli_parsers/types.py`, `cihub/cli_parsers/builder.py`, `.github/workflows/ai-ci-loop.yml`, `tests/test_cli_snapshots.py`, `tests/__snapshots__/test_cli_snapshots.ambr`, `tests/snapshots/cli_help.txt` | None                                      | CLI surface approved; includes workflow wrapper |
| **Test Reorg (6)**           | *(archived)*                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `archive/TEST_REORGANIZATION.md`          | Archived (complete)                             |
| **Doc Automation (7)**       | *(report only)*                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | `archive/DOC_AUTOMATION_AUDIT.md`         | Archived; validate gaps only                    |

### Coordination Rules

- Check `git status` before starting; do not overwrite unrelated in-flight changes.
- Declare file ownership for each workstream; avoid overlapping edits without explicit coordination.
- When a change affects shared docs, update them together: `docs/development/MASTER_PLAN.md`, `docs/development/status/STATUS.md`, `AGENTS.md`, `docs/development/CHANGELOG.md`.
- Major design decisions require ADR updates and a MASTER_PLAN “Current Decisions” update.

### Test Count Policy

- Test counts in docs are tool-generated; update via `cihub hub-ci test-metrics --write` after a verified pytest+coverage run (no manual edits).

### Document Hierarchy (Updated 2026-01-19)

```
MASTER_PLAN.md
├── WHAT to do and IN WHAT ORDER
├── High-level status tracking
└── Cross-cutting architectural decisions

Individual Planning Docs (Priority Order)
├── #1 CLEAN_CODE.md (ARCHIVED) → HOW to implement architecture improvements
├── #2 SYSTEM_INTEGRATION_PLAN.md (ARCHIVED) → HOW to fix registry/wizard disconnect
├── #3 TEST_REORGANIZATION.md (ARCHIVED) → HOW to restructure 2100+ tests
├── #4 DOC_AUTOMATION_AUDIT.md (ARCHIVED) → HOW to implement doc automation
├── #5 CLI_WIZARD_SYNC_AUDIT.md (ARCHIVED) → HOW to align wizard/CLI/schema/TS
├── #6 TYPESCRIPT_CLI_DESIGN.md (ACTIVE) → HOW to build TypeScript CLI
├── #7 AI_CI_LOOP_PROPOSAL.md (DRAFT) → HOW to build autonomous CI loop
└── #8 PYQT_PLAN.md (DEFERRED) → HOW to build GUI
```

**Rule:** When MASTER_PLAN.md and an individual doc conflict on implementation details, the **individual doc wins**. MASTER_PLAN.md may be stale on details but should be current on priorities.

---

## Active Design Docs - Priority Order

> **Work on these IN ORDER. Each doc blocks the next.** Updated 2026-01-19.

### Priority 1: CLEAN_CODE.md (ARCHIVED)

**Status:** Archived (complete) | **Blocks:** None  

```
docs/development/archive/CLEAN_CODE.md
```

Must complete **before** starting other docs:
- [x] Part 2.2: Centralize Command Output [x] **DONE** (45→7 prints, 84% reduction)
- [x] Part 2.7: Consolidate ToolResult [x] **DONE** (unified in `cihub/types.py`)
- [x] Part 5.2: Mixed Return Types [x] **DONE** (all commands → pure CommandResult)
- [x] Part 9.3: Schema Consolidation [x] **DONE** (sbom/semgrep → sharedTools, toolStatusMap extracted)
- [x] Part 7.1: CLI Layer Consolidation [x] **DONE** (factory in common.py, findings done in Part 2.2/5.2)
- [x] Part 7.2: Hub-CI Subcommand Helpers [x] **DONE** (helpers exist, ensure_executable now used)
- [x] Part 7.3: Utilities Consolidation [x] **DONE** (project.py, github_context.py, safe_run() + 34 migrations)
- [x] Part 5.3: Special-Case Handling [x] **DONE** (ToolAdapter registry in cihub/tools/registry.py)
- [x] Part 7.4: Core Module Refactoring **DONE** (8 findings)
- [x] Part 7.5: Config/Schema Consistency [x] **DONE** (schema validation bypass fixed)
- [x] Part 7.6: Services Layer **DONE** (4 findings)
- [x] Part 9.1: Scripts & Build System [x] **DONE** (deprecation warnings added)
- [x] Part 9.2: GitHub Workflows Security [x] **DONE** (harden-runner toggle)

**Why first:** Python CLI JSON output must be clean before TypeScript CLI can parse it.

### Priority 2: SYSTEM_INTEGRATION_PLAN.md (Archived)

**Status:** Archived (complete) | **Depends on:** CLEAN_CODE.md (archived) | **Blocks:** TEST_REORGANIZATION  

```
docs/development/archive/SYSTEM_INTEGRATION_PLAN.md
```

> **Note:** This consolidates the former REGISTRY_AUDIT_AND_PLAN.md, WIZARD_IMPROVEMENTS.md, and COMPREHENSIVE_SYSTEM_AUDIT.md into a single actionable plan.

Core implementation needed:
- [x] Phase 0: Safety + JSON purity (registry keys, --json guard/tests)
- [x] Phase 1: Critical fixes & CLI wrappers (min_score normalization, hub-ci wrappers, cihub block)
- [x] Phase 2: Registry schema + service (full config scope, .ci-hub.yml override detection)
- [x] Phase 3: Registry bootstrap + drift detection
- [x] Phase 4: Wizard parity + profile integration
- [x] Phase 5: CLI management commands (profile/registry/tool/threshold/repo) (2026-01-12)
- [x] Phase 6: Schema extensibility (custom tools end-to-end) (2026-01-12: added tests)

**Status:** 100% complete (2026-01-12). All phases implemented with 102 new tests.  

### Priority 3: TEST_REORGANIZATION.md (ARCHIVED)

**Status:** ARCHIVED (2026-01-17) | Phase 4 property tests complete (11/11 critical modules); Phase 5 Test Architecture section added to MASTER_PLAN.md  

```
docs/development/archive/TEST_REORGANIZATION.md
```

Completed:
- [x] Phase 4: Property tests for all 11 critical modules (196 tests passing)
- [x] Phase 5: Test Architecture section added to MASTER_PLAN.md
- [x] Dynamic schema key loading to prevent drift
- [x] 3 automation scripts (`scripts/update_test_metrics.py`, `scripts/generate_test_readme.py`, `scripts/check_test_drift.py`)

**Superseded by:** Test Architecture section in MASTER_PLAN.md  

### Priority 4: DOC_AUTOMATION_AUDIT.md (ARCHIVED)

**Status:** Archived (complete; duplicate task detection remains disabled) | **Depends on:** Stable CLI surface  

```
docs/development/archive/DOC_AUTOMATION_AUDIT.md
```

Core MVP:
- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) - Modularized package (6 modules, 63 tests including 15 Hypothesis)
 - [x] Optional `--output-dir`, `--tool-output`, `--ai-output` flags for artifact outputs [x] (2026-01-09)
- [x] `cihub docs audit` - [x] **COMPLETE** (2026-01-10) - Modular package (7 modules, 39 tests)
 - [x] Lifecycle validation (J/L/N): active/STATUS.md sync, ADR metadata, references [x]
 - [x] Part 12.J: Specs hygiene - REQUIREMENTS.md headers [x]
 - [x] Part 12.Q: Universal doc header enforcement [x]
 - [x] Part 13.R: Metrics drift detection [x]
 - [x] Part 13.S: Duplicate task detection (fuzzy matching) [x] (disabled pending cleanup)
 - [x] Part 13.T: Timestamp freshness validation [x]
 - [x] Part 13.V: Placeholder detection [x]
 - [x] Part 13.U: Checklist-reality sync [x] (2026-01-10)
 - [x] Part 13.W: Cross-doc consistency (README ↔ active/) [x] (2026-01-10)
 - [x] Part 13.X: CHANGELOG validation [x] (2026-01-10)
 - [x] Part 12.M: Doc inventory output (`docs audit --inventory`) [x] (2026-01-17)
 - [x] Guide command validation in `docs audit` [x] (2026-01-17)
- [x] Default wiring into `cihub check --audit` [x] (with skip_references, skip_consistency for fast lane)

**Why fourth:** Documentation automation needs stable command signatures.

### Priority 5: CLI_WIZARD_SYNC_AUDIT.md (ARCHIVED)

**Status:** Archived (2026-01-19) | **Depends on:** CLEAN_CODE.md (archived) + TEST_REORGANIZATION.md (archived) | **Unblocks:** TYPESCRIPT_CLI_DESIGN.md Phase 6

```
docs/development/archive/CLI_WIZARD_SYNC_AUDIT.md
```

**Why fifth:** Align wizard/CLI/schema/TypeScript before building interactive wizard flows.

### Priority 6: TYPESCRIPT_CLI_DESIGN.md (ACTIVE)

**Status:** Phase 6 complete (interactive wizard); Phase 7 complete (configuration); Phase 8 ready to start | **Depends on:** CLEAN_CODE.md (archived) + TEST_REORGANIZATION.md (archived) - both complete  

```
docs/development/active/TYPESCRIPT_CLI_DESIGN.md
```

Prerequisites satisfied:
- [x] CLEAN_CODE.md complete (CommandResult migration, stdout/stderr cleanup)
- [x] TEST_REORGANIZATION.md complete (property tests, test architecture docs)

**Why sixth:** TypeScript CLI consumes Python CLI JSON; needs clean output.

### Priority 7: AI_CI_LOOP_PROPOSAL.md (DRAFT)

**Status:** Draft (internal) | **Depends on:** Stable CLI output + triage bundles (CLEAN_CODE and TEST_REORGANIZATION archived)  

```
docs/development/active/AI_CI_LOOP_PROPOSAL.md
```

**Why seventh:** Autonomous loop depends on clean CLI contracts and deterministic triage outputs.

### Priority 8: PYQT_PLAN.md (Deferred)

**Status:** Reference only | **Depends on:** Everything above  

```
docs/development/active/PYQT_PLAN.md
```

**Why last:** GUI wrapper needs all CLI commands stable and tested.


---

## v1.0 Cutline

> **What must ship for v1.0 vs what is explicitly deferred.**
> Items below the cutline move to "Post v1.0 Backlog" at the end of this document.

### Quick Wins (Do First)

**CLI Commands:**
- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) Modularized package, 63 tests
- [x] `cihub docs audit` - [x] **COMPLETE** (2026-01-10) J/L/N/Q + Part 13.R/S/T/U/V/W/X, 39 tests
- [ ] `cihub config validate` - Validate hub configs
- [ ] `cihub audit` - Umbrella command (docs check + links + adr check + config validate)
- [ ] `--json` flag for all commands including hub-ci subcommands

**Documentation:**
- [x] Generate `docs/reference/TOOLS.md` from `cihub/tools/registry.py`
- [ ] Generate `docs/reference/WORKFLOWS.md` from `.github/workflows/*.yml`
- [x] Plain-text reference scan for stale `docs/...` strings [x] (via `cihub docs audit`)
- [x] Universal header enforcement for manual docs [x] (via `cihub docs audit` Part 12.Q)
- [x] `.cihub/tool-outputs/` artifacts for doc automation [x] (optional via `--output-dir`, `--tool-output`, `--ai-output`)
- [ ] Tooling integration checklist: toggle -> CLI runner (no inline workflow logic) -> tool-outputs -> report summaries/dashboards -> templates/profiles -> docs refs -> template sync tests

**Clean Code:** *(See `archive/CLEAN_CODE.md` for details - audit updated 2026-01-05)*
- [x] `_tool_enabled()` consolidation (5 implementations → 1 canonical) [x]
 - Added `tool_enabled()` to `cihub/config/normalize.py` as canonical implementation
 - Updated 4 call sites to delegate to canonical function
- [x] Gate-spec enforcement wiring (ThresholdSpec evaluation in gates.py) [x]
 - Added `_check_threshold()` helper to gates.py
 - Defined 27 ThresholdSpecs (Python: 15, Java: 12) in gate_specs.py
 - Wired 26 threshold checks (Python: 14, Java: 12) to use `evaluate_threshold` from gate_specs
 - All 155 gate-related tests pass (test_ci_engine.py + test_gate_specs.py); full suite 1804 tests pass
- [x] Language strategy extraction (Python/Java) - Complete [x]
 - Created `cihub/core/languages/` with base.py, python.py, java.py, registry.py
 - Delegation pattern: strategies delegate to existing `_run_*_tools()` functions
- Added tests covering registry, strategies, build tool detection, language detection
 - Refactored `run_ci()` to use strategy as primary dispatch
 - Updated `helpers.py` to use `strategy.get_default_tools()`
- All 3337 tests pass
- [x] Hub-CI CommandResult migration (43 functions → return CommandResult) - **Complete** [x]
 - [x] validation.py: 8 functions migrated [x]
 - [x] security.py: 6 functions migrated [x]
 - [x] smoke.py: 4 functions migrated [x]
 - [x] python_tools.py: 3 functions migrated [x]
 - [x] java_tools.py: 6 functions migrated [x]
 - [x] release.py: 16 functions migrated [x]
 - Router bug fixed (CommandResult vs int comparison)
- [x] Expand CI-engine tests (2 → 151) [x] - 118 CI engine tests + 33 strategy tests
- [x] Testing framework improvements [x] (See `archive/CLEAN_CODE.md` Part 10)
 - [x] Phase T1: conftest.py, pytest-xdist, hypothesis
 - [x] Phase T2: Parameterized tests (5 files refactored)
 - [x] Phase T3: Property-based testing (12 Hypothesis tests)
- **Total: 3337 tests passing** *(verified 2026-01-17; per docs audit)*
- [x] Output normalization - OutputRenderer infrastructure [x] (see **Architecture Consolidation** below)
 - [x] Contract enforcement test added (`test_command_output_contract.py`) - prevents regression
 - [x] **Migrated 13 major files** (~198 prints → CommandResult):
 - adr.py (16), triage.py (34), secrets.py (32), templates.py (22), pom.py (21)
 - dispatch.py (10), config_cmd.py (9), update.py (8), smoke.py (8), discover.py (8)
 - docs.py (10), new.py (10), init.py (10)
 - [x] **Code review fixes** (2026-01-05):
 - detect.py: Pure CommandResult return (no conditional JSON mode)
 - validate.py: Added YAML parse error handling (yaml.YAMLError, ValueError)
 - smoke.py: Fixed TemporaryDirectory resource leak
 - discover.py: Reordered empty check before GITHUB_OUTPUT write
 - cli.py: Error output routes to stderr (CLI best practice)
 - [x] ~~TODO: Migrate remaining 45 print() calls in 12 files~~ [x] **DONE** (45→7, 84% reduction)

**Test Reorganization:** *(See `archive/TEST_REORGANIZATION.md` for historical design; superseded by Test Architecture section below)*
- [x] Phase 4: Property tests for 11 critical modules (196 tests)
- [x] Phase 5: Test Architecture section added to MASTER_PLAN.md
- [x] 3 automation scripts created (`scripts/update_test_metrics.py`, `scripts/generate_test_readme.py`, `scripts/check_test_drift.py`)
- [x] Dynamic schema key loading to prevent drift

**Quality Gate Consistency:**
- [ ] Summary vs report validator: compare `summary.md` gate rows to `report.json` + `tools_ran/tools_success`
- [ ] Self-validate after `cihub ci`: run `cihub report validate --strict` on `report.json` + `summary.md`
- [ ] Enforce report validation in `cihub check --audit` and `cihub smoke --full`
- [ ] CI gate evaluation must fail/warn when `tests_total == 0`
- [ ] Contract test: `gates.py`, `reporting.py`, and `report_validator` agree on outcomes
- [ ] Configured-but-not-run policy: decide warning vs hard-fail and enforce consistently
- [ ] `fail_on_not_run` policy flag (global + per-tool) with enforcement in gates/summary/triage
- [ ] Threshold completeness rule: no `-` values in summaries; validator fails on missing thresholds
- [ ] Gate result semantics: decide `tools_success` meaning vs adding `gate_results` block
- [ ] Threshold sanity checks: warn/fail for permissive production thresholds (fixtures exempt)
- [x] Artifact-first triage (`cihub triage --run/--workflow/--branch`) with report validation + mismatch warnings [x]
- [x] Artifact evidence audit in triage (non-empty tool outputs, expected fields) [x]
- [x] Multi-report triage aggregation (`cihub triage --multi --reports-dir`) [x]
- [x] Per-tool evidence (configured/ran/required/result) with human-readable explanations [x]
- [ ] Gate toggle visibility in summaries (expose effective gate flags or load config alongside report)
- [x] Build tool status: reflect real build state in Tools Enabled + gates (not always Ran=true) [x]
- [x] CVSS parsing + gating: extract max CVSS from OWASP/Trivy reports and enforce `*_cvss_fail` [x]
- [x] JSON schema validation at runtime (`cihub report validate --schema`) [x]

**Security/CI Hygiene:**
- [ ] Pin `step-security/harden-runner` versions (21 uses)
- [ ] Standardize all action version pins
- [ ] Workflow input contract tests: ensure `.github/workflows/*-ci.yml` cover all `TOOL_KEYS` + `THRESHOLD_KEYS`
- [ ] Template artifact guard: templates must upload `report.json` + `.cihub/tool-outputs/*`
- [x] CommandResult CI enforcement: `cihub hub-ci enforce-command-result` [x] (ADR-0042)
 - Added CLI command to detect print() calls in commands/
 - Added workflow job `enforce-command-result` to hub-production-ci.yml
 - Enforces max 7 allowed prints (intentional exceptions documented)
- [x] Config validation order fix [x] (ADR-0047)
 - Validate BEFORE normalize at each config layer
 - Catches invalid input that normalization would mask
 - Clear error messages with layer names
- [ ] Subprocess timeout policy implementation (ADR-0045)
 - 33+ subprocess calls missing timeouts identified in INCONSISTENCY.md
 - Tiered timeouts: Quick (30s), Network (120s), Build (600s), Extended (900s)

### Heavy Lifts (After Quick Wins)

- [x] Output/summary context wrapper (`OutputContext` for GITHUB_OUTPUT/GITHUB_STEP_SUMMARY) [x]
- [ ] Env/context wrapper (`GitHubEnv` for 17 other `GITHUB_*` reads - extend `github_context.py`)
- [ ] Runner/adapter boundaries (subprocess only in `ci_runner/`)
- [ ] "No inline logic" workflow guard
- [ ] Performance guardrails for docs stale/audit (<5s on ~28k corpus)

### Verification (Final Step)

- [ ] Re-run hub production workflows after all v1.0 changes
- [ ] Record smoke test + pytest results in STATUS.md

---

## Current Focus (ADR-0035)

- [x] Implement triage bundles + priority output + LLM prompt pack (behind `CIHUB_EMIT_TRIAGE` env toggle).
- [ ] Implement registry CLI + versioning/rollback.
- [x] Make aggregate reports resilient to failed repos (render partial summaries instead of aborting).
- [x] Implement `cihub report dashboard` (HTML + JSON output) replacing the legacy aggregate_reports shim.
- [x] Add CLI env overrides for tool toggles and summary toggle (`CIHUB_RUN_*`, `CIHUB_WRITE_GITHUB_SUMMARY`).
- [x] Add Java SBOM support (schema + CLI runner + workflow wiring).
- [x] Toggle audit + enforcement:
 - [x] Align defaults for `repo.dispatch_enabled`, `repo.force_all_tools`, and `python.tools.sbom.enabled`.
 - [x] Add notifications env-var names to schema/defaults and CLI.
 - [x] Warn when reserved optional feature toggles are enabled.
 - [x] Gate hub-production-ci jobs via `cihub hub-ci outputs`.
- [x] Ensure workflow toggles install required CLIs (Trivy) and wire bandit severity env toggles.
- [x] Implement `run_codeql`/`run_docker` execution (CodeQL actions in reusable workflows + docker-compose runner in `cihub ci`, with fail-on-error gates).
- [x] Align `hub-run-all.yml` with CodeQL/Trivy toggles and optional per-repo detail output.
- [x] Add `docker.fail_on_missing_compose` gate and mark missing report artifacts as `missing_report` in aggregation summaries.
- [x] Add optional per-repo detail output for orchestrator aggregation (`--details-output` + `--include-details`).
- [x] **No-inline workflow cleanup:**
 - [x] Wire summary toggle in `hub-run-all.yml` summary job (`CIHUB_WRITE_GITHUB_SUMMARY`).
 - [x] Replace zizmor SARIF heredoc in `hub-production-ci.yml` with `cihub hub-ci zizmor-run`.
 - [x] Remove all multi-line `run: |` blocks by moving logic into `cihub hub-ci` helpers.
 - [x] Summary commands implemented and wired:
 - `cihub report security-summary` (modes: repo, zap, overall)
 - `cihub report smoke-summary` (modes: repo, overall)
 - `cihub report kyverno-summary`
 - `cihub report orchestrator-summary` (modes: load-config, trigger-record)
 - [x] Snapshot tests in `tests/test_summary_commands.py` (19 tests) verify parity with old heredocs.
 - [x] Toggle audit tests verify `CIHUB_WRITE_GITHUB_SUMMARY` env var behavior.

## Canonical Sources of Truth

1. **Code** (`cihub/`, `schema/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is the authoritative interface documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the authoritative config contract.

> WARNING: **REGISTRY ARCHITECTURE GAP (2026-01-06):** The registry system code (`registry_service.py`, `registry.schema.json`) is currently INCOMPLETE and should NOT be considered canonical until REGISTRY_AUDIT_AND_PLAN.md Parts 4-8 are implemented. The audit found:
> - Registry only tracks 3 of 47+ values
> - Wizard ↔ Registry are disconnected
> - Schema blocks extensibility with `additionalProperties: false`
>
> **Until fixed:** Follow `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` (archived) for registry architecture reference.

## Test Architecture

> See `tests/README.md` (auto-generated via `cihub hub-ci test-metrics --write`) for current counts.

### Test Categories

| Category    | Directory            | Purpose                                                | Run Command                 |
|-------------|----------------------|--------------------------------------------------------|-----------------------------|
| Unit        | `tests/unit/`        | Fast, isolated tests for individual functions          | `pytest tests/unit/`        |
| Integration | `tests/integration/` | Tests with external dependencies (filesystem, network) | `pytest tests/integration/` |
| E2E         | `tests/e2e/`         | End-to-end workflow tests                              | `pytest tests/e2e/`         |
| Property    | `tests/property/`    | Hypothesis property-based tests for invariants         | `pytest tests/property/`    |
| Contract    | `tests/contracts/`   | API/schema contract tests                              | `pytest tests/contracts/`   |
| Regression  | `tests/regression/`  | Bug-specific regression tests                          | `pytest tests/regression/`  |

### Property Test Coverage (Critical Modules)

Property tests verify invariants that must hold for all inputs. All critical modules have invariant coverage:

| Module                        | Test File                                  | Key Invariants                            |
|-------------------------------|--------------------------------------------|-------------------------------------------|
| `config/loader/core.py`       | `test_registry_roundtrip_invariant.py`     | load_config roundtrip                     |
| `config/loader/inputs.py`     | `test_property_based.py`                   | generate_workflow_inputs                  |
| `config/normalize.py`         | `test_config_normalize_properties.py`      | idempotency, type preservation            |
| `config/merge.py`             | `test_config_merge_properties.py`          | deep_merge identity, overlay wins         |
| `report_validator/content.py` | `test_report_validation_properties.py`     | _get_nested, _parse_bool, validate_report |
| `report_validator/schema.py`  | `test_schema_validation_properties.py`     | validate_against_schema                   |
| `core/aggregation/status.py`  | `test_aggregation_status_properties.py`    | create_run_status, _status_from_report    |
| `core/gate_specs.py`          | `test_gate_specs_properties.py`            | threshold specs, comparators              |
| `utils/paths.py`              | `test_paths_utils_properties.py`           | validate_subdir security                  |
| `types.py`                    | `test_cli_output_properties.py`            | CommandResult, ToolResult contracts       |
| `services/triage/`            | `tests/property/test_triage_properties.py` | log parser, severity ordering             |

### Test Conventions

1. **Naming**: Use descriptive test IDs with `pytest.mark.parametrize` ids
2. **Markers**: Use `@pytest.mark.slow` for tests > 5s, `@pytest.mark.integration` for external deps
3. **Metrics**: Run `cihub hub-ci test-metrics --write` to regenerate `tests/README.md`
4. **Coverage**: Targets defined in `config/defaults.yaml` under `thresholds`

### Tool Audit Plan

See `TOOL_TEST_AUDIT_PLAN.md` for the CLI-first tool testing plan. Audit execution
is logged in `docs/development/research/CIHUB_TOOL_RUN_AUDIT.md` and
`docs/development/research/TS_CLI_FULL_AUDIT_2026-01-19.md`.

## References (Background Only)

**Design Docs (Active + Archived references):**
- `docs/development/archive/CLI_WIZARD_SYNC_AUDIT.md` (wizard/CLI/schema/TS alignment audit)
- `docs/development/active/TYPESCRIPT_CLI_DESIGN.md` (TypeScript interactive CLI - consumes Python CLI as backend)
- `docs/development/active/AI_CI_LOOP_PROPOSAL.md` (autonomous AI CI loop proposal)
- `docs/development/active/PYQT_PLAN.md` (PyQt concept scope)
- `docs/development/archive/CLEAN_CODE.md` (architecture improvements: polymorphism, encapsulation)
- `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` (wizard↔registry integration, schema expansion - archived)
- `docs/development/archive/TEST_REORGANIZATION.md` (test suite restructuring - archived)
- `docs/development/archive/DOC_AUTOMATION_AUDIT.md` (doc automation design: `cihub docs stale`, `cihub docs audit`)

**Architecture:**
- `docs/development/architecture/ARCH_OVERVIEW.md` (current architecture overview)
- `docs/development/archive/ARCHITECTURE_PLAN.md` (archived deep-dive plan)
- `ARCHITECTURE_AUDIT.md` (current architecture audit and fix plan)

These are references, not competing plans.

---

## Current Decisions

- **CLI is the execution engine**; workflows are thin wrappers.
- **AI enhancement is optional and CLI-local** (`cihub/ai`, `--ai`, `CIHUB_AI_PROVIDER`, `CIHUB_DEV_MODE`) (ADR-0058).
- **Interactive clients consume the CLI command registry** (`cihub commands list --json`) (ADR-0059).
- **Wizard handoff uses CLI config payload flags** (`--config-json`/`--config-file` on `init`, `new`, `config edit`) (ADR-0060).
- **Pytest args/env are config-driven** (`python.tools.pytest.args`/`python.tools.pytest.env`) for headless/UI control (ADR-0062).
- **Headless Qt defaults are automatic** (xvfb + Qt env + optional `qprocess` skip) when Qt deps detected on Linux (ADR-0064).
- **isort uses the Black profile when Black is enabled** in config (ADR-0063).
- **GitHub auth tokens fall back to `gh auth token`** when env tokens are missing (ADR-0065).
- **CI outputs are mirrored to `GITHUB_WORKSPACE`** when needed for reusable workflow artifacts (ADR-0066).
- **Hidden `.cihub` artifacts are uploaded** in reusable workflows (ADR-0067).
- **Failure reports are always emitted** and hub workflows default `hub_repo`/`hub_ref` when missing (ADR-0074).
- **Maven multi-module tool prep** runs `mvn -DskipTests install` before plugin tools (ADR-0068).
- **Monorepo targets** use `repo.targets` for multi-language/subdir runs with per-target summaries (ADR-0069).
- **Tool evidence is explicit** via `tool_evidence` in reports for proofed tool runs (ADR-0070).
- **Hub repo vars are verified on init/setup**; failure blocks setup to prevent drift (ADR-0072).
- **Caller workflows can pin a reusable workflow ref per repo** via `repo.hub_workflow_ref` and `--hub-workflow-ref` (ADR-0073).
- **Workflow dispatch/watch lives in the CLI** (`cihub dispatch`) with wizard wrappers (ADR-0055).
- **Schema is the source of truth for defaults**; defaults.yaml and fallbacks.py are generated and audited in `cihub check --audit`.
- **Canonical install default is PyPI**; align CLI defaults and templates to schema `install.source`.
- **v1.0 languages are Java/Python only**; defer Node/Go until strategies exist (schema must reflect supported languages).
- **Command registry exposes interactive + runtime JSON support** (e.g., `supports_interactive`, `supports_json_runtime`) so clients do not rely on argparse flags.
- **Hub CI supports per-module threshold overrides** under `hub_ci.thresholds.overrides` (ADR-0054).
- **Docs audit inventory + guide command validation** live in the CLI (`cihub docs audit --inventory`) (ADR-0056).
- **Single entrypoint workflow is `hub-ci.yml`**; it routes to `python-ci.yml`/`java-ci.yml` internally.
- **Local verification uses CLI scaffolding + smoke**; fixtures repo is for CI/regression, not required for local tests.

### CLI as Headless API (Architecture Principle)

> **Added 2026-01-05:** This principle is critical for understanding why CLI commands shouldn't be restructured.

The Python CLI is designed as a **headless API backend** for future frontends:

1. **TypeScript CLI** (`docs/development/active/TYPESCRIPT_CLI_DESIGN.md`) maps slash commands to Python commands:
 - `/fix-pom` → `cihub fix-pom --json`
 - `/setup-secrets` → `cihub setup-secrets --json`
 - `/config-outputs` → `cihub config-outputs --json`

2. **PyQt6 GUI** (`docs/development/active/PYQT_PLAN.md`) calls Python CLI programmatically:
 - `cihub fix-pom`, `cihub fix-deps`, `cihub setup-secrets`, `cihub setup-nvd`
 **PYQT6 Deferred for now**

3. **GitHub Workflows** call CLI commands directly:
 - `hub-ci.yml`: `cihub config-outputs --repo . --github-output`
 - `hub-production-ci.yml`: 15+ `cihub hub-ci *` subcommands

**Implication:** CLI command names are **stable API contracts**. Restructuring (e.g., `setup-secrets` → `setup secrets`) would break:
- TypeScript CLI command mapping
- PyQt GUI subprocess calls, **pyqt6 deferred for now**
- GitHub workflow steps
- 40+ documentation files

**Safe changes only:**
- Help text wording
- `--help` output groupings
- Swapping `doctor`/`preflight` prominence (neither used in workflows/UIs)

See `CLEAN_CODE.md` Part 5.4 for full audit details.

---

## Near-Term Priorities (In Order)

### 1) Plan Consolidation (Immediate)

- [x] Create this file as the canonical plan.
- [x] Add reference banners to `docs/development/active/PYQT_PLAN.md` and `docs/development/archive/ARCHITECTURE_PLAN.md` stating this plan is canonical.

### 2) CLI as Source of Truth (Core)

- [x] Implement CLI helpers:
 - `cihub preflight` (doctor alias)
 - `cihub scaffold <type>`
 - `cihub smoke [--full]`
- [ ] Commit CLI helpers.
- [x] Add CLI doc generation commands:
 - `cihub docs generate` -> `docs/reference/CLI.md`, `CONFIG.md`, `ENV.md`, `WORKFLOWS.md`
 - `cihub docs check` for CI drift prevention
- [x] Add `cihub check` command (local validation suite: preflight → lint → typecheck → test → actionlint → docs-check → smoke)
- [ ] Optional CLI utilities: see **6) CLI Automation** below

### 3) Documentation Cleanup (Controlled Sweep)

- [x] Create `docs/README.md` as index of canonical vs reference vs archive.
- [x] Merge overlapping guides into **one** user entry point:
 - `docs/guides/GETTING_STARTED.md` is canonical user entry point.
 - Folded in ONBOARDING, MODES, DISPATCH_SETUP (now archived with superseded banners).
 - MONOREPOS, TEMPLATES, KYVERNO kept as advanced references.
 - `docs/guides/TROUBLESHOOTING.md` kept separate.
- [x] Archive `CONFIG_REFERENCE.md` (superseded by generated `CONFIG.md`).
- [x] Archive `docs/development/architecture/ARCHITECTURE_PLAN.md`.
- [ ] Move remaining legacy/duplicate docs to `docs/development/archive/` with a superseded header (no deletion).
- [x] Archive legacy dispatch templates under `templates/legacy/` and update docs/tests to match.
- [x] Make reference docs generated, not hand-written (CLI/CONFIG/WORKFLOWS/TOOLS done).
 - [x] Generate `docs/reference/TOOLS.md` from `cihub/tools/registry.py` via `cihub docs generate`.
 - [x] Generate `docs/reference/WORKFLOWS.md` (triggers/inputs tables) from `.github/workflows/*.yml`.
 - Keep `guides/WORKFLOWS.md` narrative-only; tables go in generated reference.
 - Status docs: `development/status/STATUS.md` is single source for active design docs.
 - [x] Consolidate specs into `docs/development/specs/REQUIREMENTS.md` (P0/P1/nonfunctional archived).
 - [x] Mark `docs/development/research/RESEARCH_LOG.md` as historical reference.
 - Architecture docs: keep `docs/development/architecture/ARCH_OVERVIEW.md` as active reference.

### 4) Staleness Audit (Doc + ADR)

- [x] Run a full stale-reference audit (docs/ADRs/scripts/workflows). → See `status/STATUS.md`
- [x] Record findings in a single audit ledger (`docs/development/archive/audit.md`).
- [x] Update ADRs that reference old workflow entrypoints and fixture strategy.
- [x] Fix inaccurate config references (pytest.threshold, nvd_api_key_required).
- [x] Fix broken internal links (ARCH_OVERVIEW.md smoke test link).
- [ ] Add superseded banners to archive files (CONFIG_REFERENCE, DISPATCH_SETUP, MODES, ONBOARDING).
- [ ] Review ADR-0005 (Dashboard) status - still "Proposed" after 2+ weeks.
- [ ] Clarify ADR-0035 timeline - which features are v1 vs deferred.
- [ ] Add doc drift scan for plain-text `docs/...` references to catch stale mentions (wire into `cihub check --audit`).

### 5) Verification

- [x] Run targeted pytest and record results in `docs/development/status/STATUS.md`.
- [x] Run `cihub smoke --full` on scaffolded fixtures and capture results.
- [ ] Re-run the hub production workflows as needed after CLI changes.
- [x] Define and document a local validation checklist that mirrors CI (`cihub check` + `make check` + GETTING_STARTED.md section).
- [x] Capture a CI parity map in the plan (localizable vs CI-only per hub-production step).

### 6) CLI Automation (Drift Prevention)

- [x] Add pre-commit hooks: actionlint, zizmor, lychee
- [x] Fix stale doc links (TOOLS.md, TEMPLATES.md, TROUBLESHOOTING.md, DEVELOPMENT.md pointed to archived guides)
- [x] `cihub docs links` - Check internal doc links (offline by default, `--external` for web)
- [x] `cihub adr new <title>` - Create ADR from template with auto-number
- [x] `cihub adr list` - List all ADRs with status
- [x] `cihub adr check` - Validate ADRs reference valid files
- [x] `cihub verify` - Contract check for caller templates and reusable workflows (optional remote/integration modes)
- [x] `cihub hub-ci badges` - Generate/validate CI badges from workflow artifacts.
- [ ] `cihub config validate` (or `cihub validate --hub`) - Validate hub configs (resolves validate ambiguity)
- [ ] `cihub audit` - Umbrella: docs check + links + adr check + config validate
- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) Modularized package, 63 tests. Design: `archive/DOC_AUTOMATION_AUDIT.md`
- [ ] `cihub docs workflows` - Generate workflow tables from `.github/workflows/*.yml` (replaces manual guides/WORKFLOWS.md)
- [x] `cihub docs audit` - [x] **COMPLETE** (2026-01-10) Wired into `cihub check --audit`:
 - [x] Every doc in `status/STATUS.md` Active Design Docs table must exist under `development/active/` [x]
 - [x] Every file under `development/active/` must be listed in STATUS.md [x]
 - [x] Files under `development/archive/` must have a superseded header [x]
 - [x] Plain-text reference scan for `docs/...` strings [x]
 - [x] Part 13.S: Duplicate task detection [x]
 - [x] Part 13.T: Timestamp freshness validation [x]
 - [x] Part 13.V: Placeholder detection [x]
 - [x] Part 13.U: Checklist-reality sync [x]
 - [x] Part 13.W: Cross-doc consistency [x]
 - [x] Part 13.X: CHANGELOG validation [x]
 - [x] Universal doc header enforcement (Part 12.Q) [x]
 - [ ] Path changes require docs/README.md + status/STATUS.md updates (optional)
- [x] Add `make links` target
- [ ] Add `make audit` target
- [x] Add a "triage bundle" output for failures (machine-readable: command, env, tool output, file snippet, workflow/job/step). *(Implemented via `CIHUB_EMIT_TRIAGE`)*
- [x] Add a template freshness guard (caller templates + legacy dispatch archive).
 - [x] PR trigger on `template-guard.yml` (validate-local job runs tests/test_templates.py + test_commands_scaffold.py)
 - [x] Render-diff tests (`TestRenderCallerWorkflow`) verify CLI output matches templates
 - [x] Contract verification (`cihub verify`) added to `cihub check --full`
 - [x] Remote sync check (`sync-templates --check`) in `cihub check --full` (skips gracefully if no GH_TOKEN)
 - [x] All 5 scaffold types tested (python-pyproject, python-setup, java-maven, java-gradle, monorepo)

### 6b) Documentation Automation (Design: `archive/DOC_AUTOMATION_AUDIT.md`)

> **Design doc:** Full requirements and architecture in `docs/development/archive/DOC_AUTOMATION_AUDIT.md`
> **Status:** ~98% complete (Priority #4)  

- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) Modularized package (6 modules, 63 tests including 15 Hypothesis)
 - [x] Python AST symbol extraction (base vs head comparison) [x]
 - [x] Schema key path diffing [x]
 - [x] CLI surface drift detection (help snapshot comparison) [x]
 - [x] File move/delete detection (`--name-status --find-renames`) [x]
 - [x] Output modes: human, `--json`, `--ai` (LLM prompt pack) [x]
- [x] `cihub docs audit` - [x] **COMPLETE** (2026-01-10) Modular package (7 modules, 39 tests):
 - [x] Validate `active/` ↔ `STATUS.md` sync [x]
 - [x] Validate `archive/` files have superseded headers [x]
 - [x] Plain-text reference scan for `docs/...` strings [x]
 - [x] ADR metadata lint (Status/Date/Superseded-by) [x]
 - [x] Universal header enforcement for manual docs (Part 12.Q) [x]
 - [x] Specs hygiene: REQUIREMENTS.md headers (Part 12.J) [x]
 - [x] Part 13.R: Metrics drift detection [x]
 - [x] Part 13.S: Duplicate task detection [x] (disabled pending cleanup)
 - [x] Part 13.T: Timestamp freshness validation [x]
 - [x] Part 13.V: Placeholder detection [x]
 - [x] Part 13.U: Checklist-reality sync [x] (2026-01-10)
 - [x] Part 13.W: Cross-doc consistency [x] (2026-01-10)
 - [x] Part 13.X: CHANGELOG validation [x] (2026-01-10)
- [x] `.cihub/tool-outputs/` artifacts for doc automation:
 - [x] `docs_stale.json` - Machine-readable stale reference report [x] (via `--output-dir` or `--tool-output`)
 - [x] `docs_stale.prompt.md` - LLM-ready prompt pack [x] (via `--output-dir` or `--ai-output`)
 - [x] `docs_audit.json` - Lifecycle/reference/consistency findings [x] (wired into `cihub check --audit`)
- [ ] Doc manifest (`docs_manifest.json`) for LLM context:
 - [ ] Path, category (guide/reference/active/archived)
 - [ ] Generated vs manual flag
 - [ ] Last-reviewed date
- [x] Generated references expansion:
 - [x] `docs/reference/TOOLS.md` from `cihub/tools/registry.py`
 - [x] `docs/reference/WORKFLOWS.md` from `.github/workflows/*.yml`

### 7) Local/CI Parity (Expand `cihub check`)

- [x] Define a CI-parity map: every hub-production-ci.yml step is either locally reproducible or explicitly CI-only.
- [x] Expand `cihub check` tiers:
 - `cihub check` (fast default)
 - `cihub check --audit` (docs links + ADR check + config/profile validation)
 - `cihub check --security` (bandit, pip-audit, gitleaks, trivy; skip if missing)
 - `cihub check --full` (audit + templates + verify-contracts + sync-templates-check + matrix keys + license + zizmor)
 - `cihub check --all` (everything)
- [x] Add optional tool detection and clear "skipped/missing tool" messaging.
- [x] Update `docs/guides/GETTING_STARTED.md` with new flags and expected runtimes.
- [x] Add `docs/guides/CLI_EXAMPLES.md` with runnable command examples.
- [ ] Evaluate `act` integration for local workflow simulation (document limitations; optional).

### 8) Services Layer (Phase 5A, PyQt6 Readiness)

- [x] Add discovery service + tests; wire `cihub discover` to services layer.
- [x] Add report validation service with **parity-first** behavior:
 - include summary parsing + summary/report cross-checks
 - include artifact fallback when metrics are missing
 - include effective-success merging for summary/tool status
 - avoid duplicate maps/logic between service and CLI
- [x] Wire `cihub report validate` to the service and keep CLI-only output/verbosity in the adapter.
- [x] Add aggregation service (Phase 5A pattern) and wire CLI adapter.
- [x] Add CI service wrapper for GUI/programmatic access (`cihub.services.ci`).
- [x] Add config service helpers for load/edit operations (`cihub.services.configuration`).
- [x] Add report summary service for GUI consumption (`cihub.services.report_summary`).
- [x] Move CI execution core into services layer; keep CLI as thin adapter.

### 8c) Core Modularization (Phase 5)

- [x] Move `badges.py`, `ci_report.py`, and `reporting.py` into `cihub/core/` with facades.
- [x] Split `ci_runner.py` into `cihub/core/ci_runner/` with facades.
- [x] Split `aggregation.py` into `cihub/core/aggregation/` with facades.
- [x] Update `cihub/core/__init__.py` re-exports for new core modules.
- [x] **Split `triage_service.py` into `cihub/services/triage/` package (1134→565 lines, 50% reduction)** [x]
 - `types.py`: ToolStatus, ToolEvidence, TriageBundle dataclasses
 - `evidence.py`: build_tool_evidence, validate_artifact_evidence
 - `detection.py`: detect_flaky_patterns, detect_test_count_regression
 - `__init__.py`: Clean facade with re-exports
 - **Reference pattern for future modularization** (see CLEAN_CODE.md Part 1.5)
- [ ] Run targeted tests for core modularization changes.

### 8d) CLI Parser Modularization (Phase 6)

- [x] Split CLI parser definitions into `cihub/cli_parsers/` without CLI surface changes.
- [x] Run CLI help snapshot check after parser split.
- [x] Add parser group registry to centralize command registration order.
- [x] Add CLI parser contract tests (handler wiring + JSON flag coverage).
- [x] Deduplicate CLI aliases to prevent drift (`doctor`/`preflight`).
- [x] Add `CIHUB_DEBUG` env toggle for developer tracebacks (opt-in).
- [x] Add `CIHUB_VERBOSE` env toggle for tool output streaming/log capture (opt-in).
- [x] Add `CIHUB_DEBUG_CONTEXT` env toggle for CLI context blocks (opt-in).

### 8e) Modularization Guardrails (CLI-First)

- [x] Canonicalize `load_ci_config`/`load_hub_config` to delegate to `cihub.config.loader` validation.
- [x] Remove `cihub.cli` imports from command modules (commands use services/utils only).
- [x] Enforce Stage 2 AST layer boundaries (core/services/commands) in tests.

### 8b) Config Ergonomics (Shorthand + Threshold Presets)

- [x] Expand shorthand booleans to enabled sections (reports, notifications, kyverno, optional features, hub_ci).
- [x] Add `thresholds_profile` presets with explicit `thresholds` overrides.
- [x] Split CVSS thresholds for OWASP/Trivy and add workflow input parity.

### 9) Triage, Registry, and LLM Bundles (New)

> **Implementation Note:** Triage bundles + prompt pack exist behind `CIHUB_EMIT_TRIAGE` env toggle.
> **Update 2026-01-06:** Triage schema bumped to `cihub-triage-v2` with `tool_evidence` and `evidence_issues` sections.
> **Registry:** See `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` for registry implementation plan (archived reference).

**Triage (Implemented):**
- [x] Define `cihub-triage-v2` schema with severity/blocker fields, tool evidence, and stable versioning. [x]
 - `tool_evidence`: per-tool configured/ran/required/result status with explanations
 - `evidence_issues`: validation warnings for tools lacking expected metrics/artifacts
 - `summary.required_not_run_count`: count of HARD FAIL (require_run but didn't run) tools
- [x] Implement `cihub triage` to emit:
 - `.cihub/triage.json` (full bundle)
 - `.cihub/priority.json` (sorted failures)
 - `.cihub/triage.md` (LLM prompt pack)
 - `.cihub/history.jsonl` (append-only run log)

**Triage Enhancements (TODO):**
- [ ] Standardize artifact layout under `.cihub/artifacts/<tool>/` with a small manifest.
- [ ] Extend `cihub triage` to surface docs drift findings from `.cihub/tool-outputs/` (category `docs`). See **6b) Documentation Automation**.
- [ ] Normalize core outputs to standard formats (SARIF, Stryker mutation, pytest-json/CTRF, Cobertura/lcov, CycloneDX/SPDX).
- [ ] Add severity map defaults (0-10) with category + fixability flags.
- [ ] Add `cihub fix --safe` (deterministic auto-fixes only).
- [ ] Add `cihub assist --prompt` (LLM-ready prompt pack from triage bundle).
- [ ] Add triage schema validation (`cihub triage --validate-schema`).
- [ ] Add retention policies (`cihub triage prune --days N`).

**Registry (See REGISTRY_AUDIT_AND_PLAN.md - Priority #2):**
> **Detailed plan:** `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` (19-part comprehensive audit - archived)
> The registry audit identified critical gaps: wizard↔registry disconnect, only 3/47+ fields tracked, etc.

- [ ] **Part 4:** Schema redesign (tool definitions via $ref, 47+ fields)
- [ ] **Part 5:** Service layer refactor (registry_service.py expansion)
- [ ] **Part 6:** Wizard ↔ Registry integration (currently disconnected)
- [ ] **Part 7:** Boolean toggle extensibility
- [ ] **Part 8:** Sync verification implementation
- [ ] Add drift detection by cohort (language + profile + hub) and report variance against expected thresholds
- [ ] Add registry versioning + rollback (immutable version history)
- [ ] Add aggregate pass rules (composite gating)
- [ ] Add post-mortem logging for drift incidents
- [ ] Add continuous reconciliation (opt-in auto-sync)
- [ ] Add RBAC guidance (defer to GitHub permissions for MVP)
- [ ] Add DORA metrics derived from history (optional)

### 10) Maintainability Improvements (From 2026-01-04 Audit)

> **Audit Source:** Multi-agent CLI/services/workflow audit + web research.
> **Principle:** All fixes stay in Python (CLI-first per ADR-0031). No composite actions or workflow logic.

**Code Deduplication (High Priority):**
- [x] Consolidate `_tool_enabled()` - 5 implementations → 1 canonical [x] *(See Quick Wins above)*
 - Canonical `tool_enabled()` added to `cihub/config/normalize.py`
 - 4 call sites now delegate to canonical function
- [x] Refactor gate evaluation (`services/ci_engine/gates.py`) - data-driven thresholds [x] *(See Quick Wins above)*
 - Added `_check_threshold()` helper wired to `gate_specs.evaluate_threshold`
 - 16 threshold checks now use centralized evaluation

**Test Coverage (High Priority):**
- [ ] Expand `test_services_ci.py` - 2 tests → 20+ tests
 - Missing: Python/Java branching, tool execution, gate evaluation, notifications, env overrides
- [x] Add dedicated unit tests for `services/ci_engine/gates.py` [x] - 161 tests in test_ci_engine.py + test_gate_specs.py
- [ ] Add dedicated unit tests for `services/ci_engine/helpers.py` (233 lines after consolidation, limited coverage)

**CLI Consistency:**
- [ ] Enable `--json` flag for `hub-ci` subcommands (remaining gaps)
 - Issue: `hub_ci.py` explicitly deletes the JSON flag parameter
- [ ] Require subcommand for `cihub config` and `cihub adr` (currently optional, confusing UX)

**Architecture (Medium Priority):**
- [x] Extract Language Strategies - `cihub/core/languages/` with polymorphic pattern [x]
 - Eliminates 38+ `if language == "python"` / `elif language == "java"` branches
 - Files: `base.py` (ABC), `python.py`, `java.py`, `registry.py`
 - 33+ tests in `test_language_strategies.py`
 - See `archive/CLEAN_CODE.md` Part 2.1 for design
- [x] CLI argument factory consolidation - `cihub/cli_parsers/common.py` [x]
 - 8 factory functions: `add_output_args`, `add_summary_args`, `add_repo_args`, `add_report_args`, `add_path_args`, `add_output_dir_args`, `add_ci_output_args`, `add_tool_runner_args`
 - `hub_ci.py`: 628 → 535 lines (93 lines, 15% reduction)
 - Refactored `report.py` and `core.py` to use factories
 - 30 parameterized tests in `test_cli_common.py`
- [x] OutputContext dataclass - `cihub/utils/github_context.py` [x] *(2026-01-05)*
 - Replaces 2-step pattern: `_resolve_output_path()` + `_write_outputs()` → `ctx.write_outputs()`
 - 32 call sites migrated across 7 hub-ci files
 - 38 tests (parameterized + Hypothesis property-based)
 - See `archive/CLEAN_CODE.md` Phase 2
- [x] Tool execution helpers - `cihub/commands/hub_ci/__init__.py` [x] *(2026-01-05)*
 - `ToolResult` dataclass for structured tool execution results
 - `ensure_executable()` consolidates 6 chmod patterns
 - `load_json_report()` consolidates 15+ JSON parsing patterns
 - `run_tool_with_json_report()` full tool execution + JSON parsing
 - 39 tests (parameterized + Hypothesis property-based)
- [x] Project utilities consolidation - `cihub/utils/project.py` [x] *(2026-01-05)*
 - `get_repo_name()` moved from 2 duplicates (ci_engine/helpers.py, report/helpers.py)
 - `detect_java_project_type()` moved from 2 duplicates
 - 37 tests (parameterized + Hypothesis property-based)

**Workflow Security (Quick Fix):**
- [ ] Pin `step-security/harden-runner` versions (21 unpinned uses across workflows)

**Centralization & Boundaries (From Audit):**
- [x] Output/Summary context wrapper - `cihub/utils/github_context.py:OutputContext` [x] *(2026-01-05)*
 - Centralizes GITHUB_OUTPUT/GITHUB_STEP_SUMMARY handling
 - `from_args()` factory + `write_outputs()`/`write_summary()` methods
 - 32 call sites migrated, 38 tests
- [ ] Env/context wrapper - extend `cihub/utils/github_context.py` with `GitHubEnv`
 - Centralizes 17 files with direct `os.environ.get("GITHUB_*")` reads
 - Property accessors for common values (repo, sha, ref, actor, etc.)
 - Can extend existing `github_context.py` module
 - Lint/test to enforce usage (no direct `GITHUB_*` reads in commands)
- [ ] Runner/adapter boundaries - All subprocess execution in `cihub/core/ci_runner/shared.py`
 - Adapters build specs; strategies orchestrate; no ad-hoc `subprocess.run` in commands
 - Add lint/test to forbid subprocess imports outside `ci_runner/`
- [x] Output normalization - OutputRenderer abstraction [x] (2026-01-05)
 - Commands return `CommandResult` with summary/details/problems
 - `cihub/output/renderers.py` - OutputRenderer ABC, HumanRenderer, JsonRenderer
 - `cli.py` uses `get_renderer(json_mode)` at lines 394-400
 - 35 tests in `tests/test_output_renderers.py` (parameterized + Hypothesis)
 - [x] Contract enforcement via `tests/test_command_output_contract.py` (17 tests)
 - AST-based detection of print() calls in commands/
 - Allowlist pattern for incremental migration (strangler fig)
 - Prevents regression on migrated files

**Performance & Enforcement (From Audit):**
- [ ] Performance guardrails for `cihub docs stale` / `cihub docs audit`
 - Target: <5s on ~28k-line docs corpus
 - Add simple perf test to keep `cihub check --audit` usable
- [ ] "No inline logic" workflow guard
 - Lint that flags multi-line `run: |` blocks in workflows (except allowlist: checkout, setup-python, pip install)
 - Reinforces ADR-0031 without composite actions
 - Wire into `cihub docs audit` or `cihub check --full`

---

## Documentation Consolidation Rules

- Do not duplicate CLI help text in markdown; generate it.
- Do not hand-write config field docs; generate from schema.
- If code and docs conflict, code wins and docs must be updated.

---

## Scope Guardrails

1. No large refactors (renames, src/ move, etc.) until workflow migration stabilizes.
2. No deleting docs; archive instead.
3. ADR alignment comes before cleanup decisions.
4. Fixtures repo stays for CI/regression; local dev uses scaffold/smoke.
5. Active design docs live in `docs/development/active/` and must be listed in `status/STATUS.md`.
6. When a design doc is implemented, move to `docs/development/archive/` with a superseded header.

---

## Open Questions

- Where should the long-term audit ledger live (root vs docs/development)?
- Which generated doc toolchain do we want (custom CLI, sphinx-click, or minimal generator)?
- Do we want a CI gate for ADR drift detection (warn vs fail)?

---

## Definition of Done (Near-Term)

- [x] CLI helpers committed and passing tests (`cihub check`, `preflight`, `scaffold`, `smoke`).
- [x] `docs/reference/CLI.md` and `docs/reference/CONFIG.md` generated from code.
- [x] `docs/README.md` exists and clarifies doc hierarchy.
- [x] Guides consolidated into a single entry point (`GETTING_STARTED.md`).
- [x] ADRs updated to reflect `hub-ci.yml` wrapper and CLI-first execution.
- [ ] Smoke test and targeted pytest results recorded.
- [x] Local validation checklist documented and used before push (`make check` + GETTING_STARTED.md).
- [x] Pre-commit hooks: actionlint, zizmor, lychee.
- [x] CLI automation: `docs links` (with `--external` flag, fallback to Python).
- [x] CLI automation: `adr new/list/check` commands.
- [ ] CLI automation: `config validate`, `audit` (remaining).

---

## Post v1.0 Backlog

> **Explicitly deferred.** These items are valuable but not blocking v1.0 release.
> Move to v1.0 Cutline when ready to prioritize.

### Registry & Versioning
- [ ] Implement registry CLI + versioning/rollback (`cihub registry list/show/set/diff/sync`)
- [ ] Add `config/registry.json` (Ask First before implementing)
- [ ] Add drift detection by cohort (language + profile + hub)
- [ ] Add registry versioning + rollback (immutable version history)

### Triage Enhancements

**Remote Run Analysis (CLI-First, ADR-0035 aligned):**

> **Status:** Full artifact-first implementation complete. Tool evidence + multi-report aggregation implemented.  

- [x] Add `cihub triage --run <run_id>` - Basic implementation (log parsing fallback)
- [x] Add `cihub triage --artifacts-dir <path>` - Offline mode (basic support)
- [x] Add `cihub triage --repo <owner/repo>` - Target different repository
- [x] Add `cihub triage --multi --reports-dir <path>` - Multi-report aggregation mode

**Artifact-First Triage (Implemented):**
- [x] **Per-tool evidence**: `tool_evidence` section in triage.json shows configured/ran/required/result status
 - `ToolStatus` enum: PASSED, FAILED, SKIPPED, REQUIRED_NOT_RUN, NOT_CONFIGURED
 - Human-readable explanations for each tool's status
 - Includes tool metrics and artifact presence info
- [x] **Artifact evidence validation**: `validate_artifact_evidence()` warns when tools lack evidence
 - Warns when ran+success but no metrics/artifacts
 - Info note when failed tool has no artifacts for debugging
- [x] **Multi-report aggregation**: `aggregate_triage_bundles()` for orchestrator runs
 - Summarizes pass/fail across N repos
 - `failures_by_tool`: which tools failed in which repos
 - `failures_by_repo`: which repos failed which tools
 - Generates markdown summary table

**Production Enhancements (Remaining):**
- [x] **Artifact-first strategy**: Download artifacts before falling back to logs [x]
 - `gh run download <run_id>` to fetch `*-ci-report` artifacts
 - Parse `report.json`, `summary.md`, `tool-outputs/*.json` from each artifact
 - Only fall back to `--log-failed` if no artifacts exist
- [x] **Multi-repo/matrix support**: Handle orchestrator runs with multiple repos [x]
 - `hub-run-all` uploads one artifact per repo (e.g., `repo-name-ci-report`)
 - `hub-orchestrator` uploads dispatch metadata
 - Produce one triage bundle per repo OR a merged aggregate view
 - `--multi --reports-dir` merges all repo bundles into single multi-triage.json
- [ ] **CI parity**: Same bundle shape for local and remote
 - Local: reads from `.cihub/report.json`
 - Remote: downloads to temp dir, reads same structure
 - Both produce identical `triage.json`, `priority.json`, `triage.md`
- [ ] **Auth/opt-in**: Require explicit flag/env for remote fetch
 - Default mode stays local/offline
 - `--run` requires `GH_TOKEN` or authenticated `gh` CLI
 - Add `--no-fetch` to skip artifact download and use cached
- [ ] **Graceful gaps**: Handle missing data properly
 - If `report.json` missing: add `missing_report` failure, note any tool outputs found
 - If artifacts AND logs missing: fail with clear message
 - If some repos succeeded and some failed: include both in aggregate
- [ ] **Performance/safety**:
 - Limit download size (skip artifacts > 100MB)
 - Allow `--artifacts-dir` to reuse already-downloaded artifacts
 - Add timeouts for remote operations (default 60s)
- [ ] Add `cihub triage --workflow <name>` - Analyze latest failure from named workflow
- [ ] Add `cihub triage --branch <branch>` - Analyze latest failure on branch

**Schema & Retention:**
- [ ] Add triage schema validation (`cihub triage --validate-schema`)
- [ ] Add retention policies (`cihub triage prune --days N`)
- [ ] Add aggregate pass rules (composite gating)
- [ ] Add post-mortem logging for drift incidents
- [ ] Add continuous reconciliation (opt-in auto-sync)

**Output Normalization:**
- [ ] Normalize core outputs to standard formats (SARIF, Stryker, pytest-json, Cobertura, CycloneDX)
- [ ] Add severity map defaults (0-10) with category + fixability flags
- [ ] Add `cihub fix --safe` (deterministic auto-fixes only)
- [ ] Add `cihub assist --prompt` (LLM-ready prompt pack from triage bundle)

### Governance & Metrics
- [ ] Add RBAC guidance (defer to GitHub permissions for MVP)
- [ ] Add DORA metrics derived from history (optional)
- [ ] Add flaky test detection + test-count drop alerts from triage history (CLI-first)

### Optional Tooling
- [ ] Evaluate `act` integration for local workflow simulation (document limitations)
- [ ] Doc manifest (`docs_manifest.json`) for LLM context (path, category, generated flag, last-reviewed)

### CLI/Wizard Roadmap (Post v1.0, Phased)

**Architecture alignment:** CLI-first, schema-driven defaults, CommandResult outputs, wizard wraps CLI handlers.
Workflow changes are only allowed as thin wrappers that call `cihub ...` (no inline logic).

#### Phase A: CLI UX Quick Wins (No schema change)
- [ ] `cihub hooks generate` / `cihub hooks install` to generate `.pre-commit-config.yaml` from enabled tools.
 - Implementation: derive from tool registry + resolved config; allow opt-in tool selection.
- [ ] `cihub ci --dry-run` to emit an execution plan (tools, versions, config sources).
 - Implementation: reuse language strategies to list planned tool runs, no execution.
- [ ] `cihub config diff --repo A --repo B` to compare resolved configs.
 - Implementation: load both configs via config service and diff normalized output.
- [ ] Wizard/CLI parity: every wizard prompt has a CLI flag or non-interactive default.
 - Implementation: align wizard questions with `cihub config set`/`cihub init` flags.
- [ ] Wizard: profile preview during selection + "what changed" diff at end.
 - Implementation: reuse config diff output in wizard summary.
- [ ] Wizard: copy config from another repo (seed setup).
 - Implementation: choose repo -> load resolved config -> override repo metadata.
- [ ] Wizard: quick edit mode for single setting/tool.
 - Implementation: select target field -> write config -> summary diff.
- [ ] Wizard UX: progress indicator, accept defaults, inline help, and resume support.
 - Implementation: keep wizard state in temp file; add `--resume` flag.
- [ ] CLI UX: progress indicators for long-running runs (human output only).
 - Implementation: OutputRenderer-driven status (no prints in commands).
- [ ] Standardize `--quiet`/`--verbose` flags across commands.
 - Implementation: map to OutputRenderer settings and `CIHUB_VERBOSE`.
- [ ] Shell autocompletion (`cihub completion bash|zsh|fish`).
 - Implementation: generate from argparse (optional extra dependency).
- [ ] Missing tool prompt standardization.
 - Implementation: extend `--install-missing` to prompt/skip across commands.
- [ ] Preview/backup for destructive ops (`--diff`, `--backup`, `cihub config revert`).
 - Implementation: add to file-modifying commands only.
- [ ] `cihub config lint` (best-practices warnings, non-blocking).
 - Implementation: new service rule set (missing security tools, permissive thresholds).

#### Phase B: Schema + Validation Enhancements (ADR required)
- [ ] Publish schema to SchemaStore + add `$schema` in generated configs.
 - Implementation: release process + schema metadata update.
- [ ] Semantic validation rules (beyond schema).
 - Implementation: extend `cihub config lint` with hard/soft warnings (ex: mutation enabled but tests disabled).
- [ ] Config inheritance/includes (extends/includes).
 - Implementation: must align with profiles/registry to avoid multiple sources of truth.
- [ ] Env var interpolation for config values (opt-in).
 - Implementation: explicit `${VAR:-default}` parsing in config loader.
- [ ] Per-tool `extra_args` passthrough in schema (e.g., `python.tools.ruff.extra_args`).
 - Implementation: extend schema/defaults + registry, pass args in tool adapters.
- [ ] Test parallelization config (pytest `-n`, surefire/gradle parallel).
 - Implementation: schema fields + strategy adapters; default off.
- [ ] Conditional tool execution (simple `depends_on` / `only_if` rules).
 - Implementation: gate in CLI tool runner before execution.

#### Phase C: Branch/Profile Overrides (ADR required)
- [ ] Branch-specific overrides in config (pattern match + override block).
 - Implementation: resolve branch from `--branch` or `GITHUB_REF`, apply overrides in config loader.
- [ ] Wizard flow to add branch overrides with preview.

#### Phase D: Scheduling + Matrix (Workflow touch required)
- [ ] Config metadata for schedules and matrices (source of truth).
 - Implementation: `cihub config-outputs` exposes derived schedule/matrix data.
- [ ] Minimal workflow templates that read schedule/matrix outputs and call `cihub ci`.
 - No inline logic; only pass outputs into CLI.
- [ ] CLI-only fallback: sequential matrix runs (no GH job fan-out).

#### Phase E: Migration + IDE + Reporting
- [ ] `cihub import --from <workflow>` best-effort config import.
- [ ] `cihub migrate --from travis|circle|jenkins` guided migration wizard.
- [ ] `cihub ide generate --vscode/--intellij` from config/tool settings.
- [ ] `cihub report render --template <path>` for custom report outputs.
- [ ] `cihub explain --run <id>` (triage summary -> human-readable explanation).
- [ ] `cihub setup --quick` to run common onboarding defaults end-to-end.
- [ ] `cihub docs serve` for local docs browsing (search optional).
- [ ] `cihub config history` (git-backed history view; read-only).
- [ ] Compliance report export (`cihub report compliance --format pdf|csv`).

#### Phase F: Drift Detection + Governance (ADR required)
- [ ] `cihub drift check` to compare config vs repo workflow/tool reality.
- [ ] `cihub drift fix` to reconcile drift (CLI-first, no YAML logic).
- [ ] Config lock header + strict verify (managed-by-cihub enforcement).
- [ ] Drift notifications (email/Teams/etc.) via optional integrations.

#### Phase G: Extensibility + Plugins (ADR required)
- [ ] Plugin registry/install for tools and profiles.
- [ ] Profile install from community registry.
- [ ] Reusable config components/templates for teams (org defaults).
- [ ] Hooks/callbacks (pre/post tool hooks) with opt-in security guardrails.
- [ ] Custom gates (prefer custom tools pattern; formalize if needed).

#### Phase H: Developer Experience + Analytics
- [ ] Local workflow simulation (tie into `act` evaluation).
- [ ] Cache guidance + cache hit reporting (CLI report metrics).
- [ ] Build time analytics per tool over time (requires storage).
- [ ] Cost estimation for GH Actions minutes before runs.
- [ ] Tool parallelization where safe (core runner changes).
- [ ] Expand `cihub fix --ai` coverage beyond current tool set.
- [ ] Threshold history/trend reporting (coverage/mutation over time).

**Out-of-architecture/needs exception (decide to adjust or drop):**
- Per-artifact retention in GH Actions requires workflow changes beyond CLI-only outputs.
- Full GH matrix fan-out requires workflow updates; CLI can only do sequential matrices.
- Live multi-repo dashboards and custom notifications require external services or workflows.
- RBAC roles are enforced by GitHub/org permissions, not the CLI.

### Codebase Quality Sweep (Post v1.0, After Test Reorg)
- [ ] Modularization sweep: reduce monoliths, improve polymorphism, clean abstractions.
- [ ] Consistency pass: CommandResult-only outputs, no print() in commands.
- [ ] Tech debt cleanup: remove dead code paths and legacy adapters after tests.

### Tooling Expansion (Security + Quality)
- [ ] DAST (ZAP) CLI-first toggle + runner:
 - Add `python.tools.zap` config + schema/defaults
 - Add CLI runner (`cihub ci`/`cihub run zap`) and tool-outputs capture
 - Replace workflow inline action usage with CLI invocation
 - Add report summaries + dashboard metrics for ZAP findings
 - Update templates/profiles + `tests/test_templates.py`
- [ ] API schema testing via Schemathesis (`python.tools.schemathesis`), CLI runner + report metrics
- [ ] Python env managers (poetry/pdm/uv) support in install strategy
- [ ] `tox` support for multi-environment testing
- [ ] Pre-commit integration (`cihub init --pre-commit`) + config template support
- [ ] Optional `pre-commit` run as a CI tool (`python.tools.pre_commit`)
- [ ] API docs generation (`cihub docs generate --api` via pdoc or equivalent)
- [ ] Deep linting (`python.tools.pylint`) as optional complement to Ruff
- [ ] Python: pytest-benchmark, nbqa (notebook validation), sphinx build checks
- [ ] Java: Error Prone, ArchUnit, Testcontainers awareness, Maven Enforcer
- [ ] Java: Kotlin-aware detection/strategy for mixed projects
- [ ] Publishing: JFrog/Nexus artifact publish (optional, infra-dependent)
- [ ] Quality dashboards (SonarQube integration; optional, infra-dependent)
- [ ] Premium DAST option (StackHawk; optional)

### PyQt6 GUI (Phase 2)
- [ ] See `active/PYQT_PLAN.md` for full scope - deferred until CLI stabilizes
