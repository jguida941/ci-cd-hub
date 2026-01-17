# Remediation Plan: Architecture and Plan Alignment (Archived)
> **Superseded by:** [MASTER_PLAN.md](../MASTER_PLAN.md)

> **WARNING: SUPERSEDED:** This intake log is archived (2026-01-15). Remediation work is complete
> or deferred to backlog. See `docs/development/MASTER_PLAN.md` and `docs/development/BACKLOG.md`.
>
> **Status:** Archived
> **Archived:** 2026-01-15
> **Owner:** Development Team
> **Source-of-truth:** manual
> **Last-reviewed:** 2026-01-15
> **Superseded-by:** docs/development/MASTER_PLAN.md

**Completion:** All phases complete. R-002-FOLLOWUP is deferred to backlog (non-blocking).

## Purpose

Central log of audit findings and remediation tasks to align CLI, wizard, schema, workflows, ADRs, and planning docs.
This is the intake doc; downstream plan docs are updated after remediation tasks are agreed and completed.

## Scope

- CLI and wizard behavior parity
- Schema/config/workflow alignment
- Distribution path (PyPI vs git) and bootstrap logic
- Documentation and ADR accuracy
- CI failures and test coverage gaps

**Note:** Test counts refreshed to 2862 after a verified full run (2026-01-15).

## Inputs Reviewed

- `docs/development/archive/CLEAN_CODE.md`
- `docs/development/archive/SYSTEM_INTEGRATION_PLAN.md`
- `docs/development/active/DOC_AUTOMATION_AUDIT.md`
- `docs/development/active/TEST_REORGANIZATION.md`
- `docs/development/MASTER_PLAN.md`
- `docs/adr/*.md`
- Local triage bundles in `.cihub/runs/*/triage.json`

## Findings (Ordered)

### Critical

- R-001 Setup scaffolding arguments are wrong, so the "new project" flow fails before scaffolding runs.
  Evidence: `cihub/commands/setup.py:196`, `cihub/commands/scaffold.py:120`.
- R-002 Setup wizard selections are discarded when writing files; Step 5 reruns init without wizard and writes defaults.
  Evidence: `cihub/commands/setup.py:303`, `cihub/commands/setup.py:338`.

### High

- R-010 Install source defaults conflict with the new PyPI architecture (schema default is `pypi`, CLI/bootstrap default is `git`).
  Evidence: `cihub/data/schema/ci-hub-config.schema.json:1156`, `cihub/cli_parsers/repo_setup.py:91`,
  `cihub/commands/init.py:114`, `scripts/install.py:62`.
- R-011 `harden_runner` config exists but is never emitted or passed through reusable workflows, so `.ci-hub.yml`
  cannot control it in distributed mode.
  Evidence: `cihub/data/schema/ci-hub-config.schema.json:1170`, `cihub/commands/config_outputs.py:123`,
  `.github/workflows/hub-ci.yml:150`, `.github/workflows/python-ci.yml:118`.
- R-012 Data paths moved to `cihub/data`, but scripts/docs still reference root `schema/` and `config/`, causing drift.
  Evidence: `cihub/utils/paths.py:8`, `scripts/validate_config.py:43`, `docs/development/archive/CLEAN_CODE.md:31`.

### Medium

- R-020 Wizard parity gap for operational commands (check, ci, triage, docs, report, verify) conflicts with architecture.
  Evidence: `docs/development/archive/SYSTEM_INTEGRATION_PLAN.md:109`, `cihub/cli_parsers/core.py:156`,
  `cihub/cli_parsers/triage.py:14`.
- R-021 Hardcoded hub repo defaults violate the no-hardcoding rule and limit multi-hub reuse.
  Evidence: `cihub/cli_parsers/secrets.py:24`, `scripts/install.py:70`.
- R-022 Global thresholds are only partially applied to workflow outputs (max_* overrides ignored in distributed mode).
  Evidence: `cihub/commands/config_outputs.py:123`, `cihub/data/schema/ci-hub-config.schema.json:704`.
- R-023 Tools reference doc generation is incomplete; `docs/reference/TOOLS.md` is manual but plan expects generation.
  Evidence: `docs/reference/TOOLS.md`, `docs/development/MASTER_PLAN.md:209`.
- R-024 ADR-0051 status is Proposed even though profile-first wizard is implemented.
  Evidence: `docs/adr/0051-wizard-profile-first-design.md:3`, `cihub/wizard/core.py:56`.

### Low

- R-030 MASTER_PLAN and CLEAN_CODE status/percentages are stale relative to code.
  Evidence: `docs/development/MASTER_PLAN.md:14`, `docs/development/archive/CLEAN_CODE.md:4`.
- R-031 Templates and workflows still use `@main` despite ADR guidance to pin tags/SHA.
  Evidence: `cihub/data/templates/repo/hub-python-ci.yml:11`, `.github/workflows/hub-ci.yml:155`,
  `docs/adr/0033-cli-distribution-and-automation.md:66`.
- R-032 Bootstrap installer uses subprocess without timeout (ADR-0045 gap).
  Evidence: `scripts/install.py:80`.
- R-033 Local CI failures: snapshot drift and coverage below gate; triage shows "UNKNOWN STEP" parser drift.
  Evidence: `.cihub/runs/21028803590/triage.json`, `.cihub/runs/21025275011/triage.json`.

## Remediation Plan

### Phase 0: Policy Decisions ✅ DECIDED 2026-01-15

- [x] **R-010 Install source**: Default is `pypi`. Aligns with ADR-0033, schema, "CLI as product" architecture.
      Git/local remain explicit overrides for dev or edge cases.
      Action: Update CLI defaults (init parser), bootstrap script, docs/ADR language.
- [x] **R-020 Wizard scope**: Add `--wizard` to operational commands (check, ci, triage, docs, report, verify).
      Implementation: Thin UI that gathers flags/options, calls same command handlers. Must reject `--json`.
      No wizard-only logic; parity with CLI flags.
- [x] **R-011 harden_runner**: Config-driven. Wire from `.ci-hub.yml` → workflows.
      Aligns with architecture: schema as contract, CLI as engine, workflows as thin wrappers.

### Phase 1: Blocking Fixes

#### R-001: Fix scaffold arg wiring ✅ COMPLETE
- [x] Fix `cihub setup` scaffold arg wiring to use `path` and required flags.
- **Code Review (Justin Guida 2026-01-15):** Must add `force=False` to namespace; scaffold.py:169 reads `args.force`.
- **Files:** `cihub/commands/setup.py` only
- **Patch:**
  ```python
  scaffold_args = argparse.Namespace(
      type=project_type,
      path=str(target_path),  # was 'dest'
      name=project_name,
      list=False,
      github=False,
      wizard=False,
      force=False,            # REQUIRED per code review
      json=False,
  )
  ```

#### R-002: Persist wizard config ✅ COMPLETE
- [x] Persist wizard selections when writing files; avoid overwriting with detected defaults.
- **Code Review #1 (Justin Guida 2026-01-15):**
  1. `init_result.data["config"]` does not exist - cmd_init never includes config in data (init.py:243-251)
  2. Must add `config` to CommandResult.data when wizard is used
  3. When `config_override` is present, set language from it BEFORE render_caller_workflow (init.py:174)
  4. Keep `config_override` internal only (no CLI surface change)
- **Code Review #2 (Justin Guida 2026-01-15):**
  1. HIGH: cmd_init must return config in CommandResult.data or setup will pass empty override
  2. HIGH: Must set language from config_override before render_caller_workflow to avoid mismatch
  3. MEDIUM: Validate config_override as dict, ignore when empty/invalid to avoid crashes
  4. MEDIUM: Adding config to --json output may change snapshots; update test_cli_snapshots.py
  5. LOW: Add setup flow regression test for wizard persistence
- **Files:** `cihub/commands/setup.py`, `cihub/commands/init.py`
- **Approach:** Option 1 (minimal) with all code review conditions. Option 3 tracked as follow-up.
- **Implementation Plan (Justin Guida 2026-01-15):**
  1. **init.py changes:**
     - Add internal `config_override` support (no parser/CLI flag)
     - Guard shape: only apply if `isinstance(config_override, dict) and config_override`
     - Apply override only when `args.wizard is False` (avoid double-wizard logic)
     - Merge: `final_config = deep_merge(detected_config, config_override)`
     - Set language from `final_config` BEFORE `render_caller_workflow`
     - Use `final_config` for payload, save_yaml_file, CommandResult
     - [x] Use final repo config values for `owner/name/branch/subdir` in CommandResult data
     - [x] Align `repo.language` to final language and drop unused language blocks after overrides
     - When `args.wizard is True`, include config in `CommandResult.data`
     - Do NOT add config to non-wizard JSON outputs (avoids snapshot churn)
  2. **setup.py changes:**
     - After Step 4, capture: `wizard_config = init_result.data.get("config", {})`
     - If empty/missing, return clear error (protect against silent loss)
     - In Step 5, pass: `init_args.config_override = wizard_config`
     - Keep `wizard=False` and `apply=True` as before
  3. **Tests (mandatory):**
     - Unit test for cmd_init override in `tests/test_init_override.py`
     - Setup flow test in `tests/test_setup_flow.py` with monkeypatched prompts

#### R-002-FOLLOWUP: Refactor init to separate detect/write (DEFERRED)
- [ ] Track as future architectural improvement: separate detect phase from write phase in init.
- **Rationale:** Cleaner long-term but larger scope; not blocking for v1.0.

#### R-001/R-002 Test Gap ✅ COMPLETE
- [x] Add regression tests for setup command flow (tests/test_setup_flow.py created).
- [x] Add unit tests for init config_override (tests/test_init_override.py created).
- **Code Review (Justin Guida 2026-01-15):** No regression test for `cihub setup --new` scaffold path; add test to cover arg wiring at setup.py:196.
- **Note:** Scaffold path test (--new) added in `tests/test_setup_flow.py`.

---

- [x] Emit and wire `harden_runner` to distributed workflows if kept in schema. (R-011) **DONE**
  - Added extraction logic to `config_outputs.py` (lines 151-162)
  - Added outputs to `hub-ci.yml` config job (lines 123-125)
  - Wired to python/java jobs (lines 186-188, 241-243)
  - Child workflows already accept inputs
- [x] Apply full global threshold overrides in `config-outputs`. (R-022) **DONE**
  - Expanded threshold loop from 4 to 12 keys (lines 123-145)
  - Now covers all max_* thresholds per schema contract

### Phase 2: Path and Doc Alignment

- [x] Update script defaults and docs to use `cihub/data` paths. (R-012) **PARTIAL** - CLEAN_CODE.md paths updated (6 fixes), remaining script refs tracked separately
- [x] Update ADR-0051 status to Accepted/Implemented. (R-024) **DONE** - Status changed to "Implemented", added Implementation Summary section
- [x] Generate TOOLS reference from tool registry and align docs generator. (R-023) **DONE**
  - Added TOOLS reference generation to `cihub docs generate`
  - `docs/reference/TOOLS.md` now generated from `cihub/tools/registry.py`
- [x] Refresh MASTER_PLAN and CLEAN_CODE status fields after fixes land. (R-030) **DONE** - Test count policy applied, File Ownership Map added

### Phase 3: CI Stabilization

- [x] Fix snapshot drift and coverage gate failures; update snapshots or tests as needed. (R-033) **DONE**
  - Fixed `hub_root` → `hub_root_path` typo in `test_registry_roundtrip_invariant.py:262`
  - Added 4 utility scripts to coverage omit in `pyproject.toml`
  - Tests passing (count tracked in STATUS.md), snapshots clean
- [x] Resolve triage "UNKNOWN STEP" mapping via run metadata. (R-033) **DONE**
  - **Root cause:** "UNKNOWN STEP" comes from GitHub CLI (`gh run view --log-failed`), NOT cihub parser
  - GitHub API sometimes returns literal "UNKNOWN STEP" instead of actual step names
  - Implemented hybrid mapping: parse logs and cross-reference `--json jobs` when "UNKNOWN STEP" detected
  - **Files updated:** `cihub/commands/triage/log_parser.py`, `cihub/commands/triage/remote.py`, `cihub/commands/triage/github.py`
  - **Tests:** `tests/test_triage_log_parser.py`, `tests/test_triage_github.py`

### Phase 4: Hardening and Backlog

- [x] Remove hardcoded hub repo defaults or route through config. (R-021) **DONE**
  - Removed hardcoded default in `setup-secrets` CLI parser; use `CIHUB_HUB_REPO`
  - `hub-ci outputs` now resolves repo from `CIHUB_REPO` or `GITHUB_REPOSITORY`
  - Caller templates now use repo variables (`HUB_REPO`, `HUB_REF`) instead of hardcoded hub repo
- [x] Pin workflow references in templates and reusable workflows. (R-031) **DONE**
  - Changed `@main` → `@v1` in `hub-ci.yml` (lines 158, 213)
  - Changed `@main` → `@v1` in template files (hub-python-ci.yml, hub-java-ci.yml)
  - Aligned template `hub_ref` defaults to `v1` for CLI/workflow consistency
  - Fixed misleading comments recommending @main
  - actionlint passes
  - Approval: explicit approval recorded before workflow edits (2026-01-15)
- [x] Add timeout handling to bootstrap installer. (R-032) **DONE**
  - Added timeout tiers in `scripts/install.py` and applied to git/pip commands
  - Removed hardcoded hub repo default; require `CIHUB_HUB_REPO` for git/local installs

## Downstream Doc Sync (After Each Phase)

- Update checklists in the active priority doc(s).
- Update `docs/development/MASTER_PLAN.md` status lines and blockers.
- Update `AGENTS.md` Current Focus if priority shifts.
- Run doc gates for doc changes: `cihub docs generate`, `cihub docs check`, `cihub docs stale`, `cihub docs audit`.
