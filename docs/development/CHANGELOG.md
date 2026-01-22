# Changelog

All notable changes to this project will be documented in this file.

## 2026-01-23 - TS CLI Passthrough + Gradle Target Fixes

### Fix: TypeScript CLI passthrough

- `cihub-cli` now passes subcommands directly to the Python CLI (e.g., `detect`, `config-outputs`, `dispatch`, `triage`).

### Fix: Gradle PITest/PMD normalization

- `cihub fix-gradle --with-configs` now infers PITest `targetClasses/targetTests` when missing or wildcarded.
- PMD normalization replaces empty rulesets with quickstart defaults.

### Fix: Triage artifact download auth

- Triage gh client now injects `GH_TOKEN` from env or `gh auth token` so artifact downloads work without manual setup.

### Fix: JaCoCo aggregate discovery

- JaCoCo runner now scans `jacoco-aggregate` reports to detect coverage in multi-module layouts.

### Fix: OWASP runs without NVD key

- OWASP runner now uses public NVD updates when no key is present, so dependency-check can still run and emit evidence.

### Fix: Hub vars verification on init/setup

- `cihub init`/`cihub setup` now fail when HUB_REPO/HUB_REF cannot be verified, preventing silent drift (ADR-0072).

### Fix: Threshold precedence for tool overrides

- Tool-specific threshold values now override default thresholds (e.g., `java.tools.checkstyle.max_errors` wins over defaults).

### Fix: Report evidence integrity checks

- Tool outputs now include `returncode`, and report validation cross-checks tool-outputs for mismatches and placeholder reports.
- OWASP no longer creates placeholder reports; fatal analyzer errors now fail the tool.

### Fix: OWASP report output + hub ref guard

- OWASP now writes JSON reports to `.cihub` with a dedicated data cache directory to reduce missing evidence.
- `cihub ci` now fails fast when `HUB_REF` is a version tag that doesn't match the installed CLI version.

### Fix: `cihub run` supports Java tools

- `cihub run` now supports Java tool runners (OWASP, PITest, Checkstyle, SpotBugs, PMD, JaCoCo) alongside Python tools.
- Added `--language` to disambiguate tools that exist in multiple runtimes.

## 2026-01-22 - Require Run Defaults

### Change: Configured tools must run

- Defaulted `require_run_or_fail` to true for all tools and the global gate.
- Added ADR-0071 documenting the policy.

## 2026-01-22 - Gradle Config Normalization

### Fix: Normalize Gradle tool blocks

- `cihub fix-gradle --with-configs` now normalizes existing PMD, PITest, and OWASP blocks even when no plugins are missing.
- OWASP Gradle configs now treat `config/owasp/suppressions.xml` as optional to avoid failing when the file is absent.
- OWASP Gradle runs no longer disable auto-update by default when no NVD key is present.
- OWASP Gradle configs now set `nvd.apiKey` only when `NVD_API_KEY` is provided to avoid 403 failures.
- OWASP runs now emit a placeholder report with a warning when NVD update fails (403/404) so CI can proceed.

## 2026-01-21 - GitHub Auth Fallback

### Fix: Dispatch token fallback via gh

- `cihub dispatch`/`cihub triage` now fall back to `gh auth token` when no env token is set.
- Token priority order recorded in ADR-0065.

### Fix: Mirror CI outputs to workspace

- `cihub ci` mirrors `.cihub` outputs to `GITHUB_WORKSPACE` when the output dir is outside the workspace (ADR-0066).

### Fix: Upload hidden CI artifacts

- Reusable workflows now upload `.cihub` artifacts by enabling `include-hidden-files` (ADR-0067).

### Fix: Maven multi-module tool prep

- `cihub ci` runs `mvn -DskipTests install` before Maven plugin tools for multi-module projects (ADR-0068).

### Fix: Auto-select git install for new config features

- `cihub init`/`cihub update` now set `install.source: git` when configs use `repo.targets` or pytest `args/env` to ensure CI installs a compatible cihub build.

### Fix: Monorepo workdir honors repo.targets language

- `cihub ci` now matches `--workdir` to `repo.targets` and uses the target language (prevents Java tools running in Python subdirs).

### Fix: Preserve repo.targets on init

- `cihub init` no longer drops `repo.targets` when re-running on an existing monorepo config.

### Fix: OWASP JSON report output

- OWASP dependency-check now forces JSON output so CI evidence is always generated.
- If dependency-check exits cleanly but emits no report, cihub writes a placeholder JSON report to keep evidence consistent.

### Fix: Multi-report verify-tools

- `cihub triage --verify-tools` now aggregates multiple report artifacts (e.g., Python + Java monorepos).

### Fix: Gate failures reflect in tool success

- Gate violations now flip `tools_success` to false so summaries/triage match quality-gate outcomes.

## 2026-01-21 - Tool Evidence + Monorepo Targets

### Fix: Verified tool evidence

- Tool evidence now requires metrics or artifacts; tools that ran without evidence are reported as `NO REPORT`.
- Java tool runners mark `ran=true` when invoked and require report evidence for success.

### Fix: Checkstyle always runs

- When a repo has no Checkstyle config, the hub default is injected so configured tools run without repo edits.

### Fix: PITest report output

- `pitest` now forces XML/HTML output formats to ensure report evidence exists.

### Fix: OWASP without NVD key

- OWASP Dependency-Check runs without NVD updates when no API key is set to avoid 403 failures; results are marked as no-report when missing.

### New: Monorepo targets

- Added `repo.targets` for multi-language, multi-subdir runs (monorepo support) with per-target summaries in reports.
- `cihub config-outputs` now emits `run_python`, `run_java`, `python_workdir`, and `java_workdir` so hub-ci can run both languages.

## 2026-01-20 - ADR + Deprecated Shim Cleanup

### Fix: ADR tooling uses project root

- `cihub adr list` now scans `docs/adr` from the repo root after the data path move.

### Change: Remove deprecated shim scripts

- Removed legacy shim scripts (aggregate_reports, apply_profile, validate_config, validate_summary, run_aggregation, verify-matrix-keys, quarantine-check, correlation, python_ci_badges, render_summary).
- Use CLI commands instead (for example: `cihub report dashboard`, `cihub report validate`, `cihub config apply-profile`, `cihub hub-ci verify-matrix-keys`).

### Fix: PyPI publish tag filter

- Publish workflow now runs only on semver tags (`v*.*.*`) to avoid triggering on the floating `v1` tag.

## 2026-01-20 - Qt System Deps for Headless CI

### Fix: Install libEGL for PySide/PyQt on Linux

- `cihub ci --install-deps` installs `libegl1` and `xvfb` when Qt GUI deps are detected (PySide/PyQt) to prevent headless import errors.
- `cihub ci --install-deps` also installs Qt/XCB runtime libraries for PySide/PyQt on Linux.
- `cihub ci` runs pytest under `xvfb-run` on Linux when Qt deps are detected and no display is available.
- `cihub ci` skips `qprocess`-marked tests automatically in headless Qt runs when no explicit `-m` marker filter is provided.
- If `xvfb-run` times out, `cihub ci` retries pytest without xvfb while keeping headless Qt env defaults.
- Bandit tool success now respects `fail_on_*` settings to avoid false failures when only low/medium issues are allowed.

## 2026-01-20 - Init Language Fallback

### Fix: Use config language when markers are missing

- `cihub init` now uses language from existing `.ci-hub.yml` or config override when repo markers are missing.

## 2026-01-20 - Java Gate Proofing

### Fix: Only gate tools that actually ran

- Java gates now evaluate checkstyle/spotbugs/pmd/pitest/jacoco only when the tool ran.
- Checkstyle is skipped with a warning when no config file is present, avoiding false failures on default setups.

## 2026-01-20 - Tool Proof Verification

### Fix: Optional tools no longer fail verify-tools

- `cihub triage --verify-tools` now respects `tools_require_run`; configured-but-optional tools that did not run are reported as optional instead of drift failures.

## 2026-01-19 - TypeScript Wizard Handoff (Phase 6)

### New: TypeScript interactive wizard flows

- Added Ink-based wizard scaffolding with step definitions and profile helpers.
- Implemented `/new`, `/init`, and `/config edit` wizard flows in the TypeScript CLI.

### Change: CLI config payload handoff

- Added `--config-json` / `--config-file` to `cihub init`, `cihub new`, and `cihub config edit` for headless wizard handoff.
- `cihub config edit` now supports JSON runtime when a config payload is supplied.
- Recorded decision in ADR-0060.

## 2026-01-19 - Onboarding Hub Vars

### Fix: Auto-set HUB_REPO/HUB_REF in setup/init

- `cihub setup` and `cihub init` now set HUB_REPO/HUB_REF repo variables via `gh` when available.
- Added `--set-hub-vars/--no-set-hub-vars` and hub override flags for setup/init.
- Documented `CIHUB_HUB_REPO` / `CIHUB_HUB_REF` in the env registry.

## 2026-01-19 - Pytest Headless Config

### New: Configurable pytest args/env

- Added `python.tools.pytest.args` and `python.tools.pytest.env` for headless CI and UI test control.
- `cihub ci` and `cihub run pytest` now pass pytest args/env from config.
- Recorded decision in ADR-0062.

## 2026-01-19 - isort Default Profile

### Change: Align isort with Black by default

- `cihub ci` and `cihub run isort` use `isort --profile black` when Black is enabled in config.
- Recorded decision in ADR-0063.

## 2026-01-19 - TypeScript CLI Configuration (Phase 7)

### New: Config loader + first-run setup

- Added `~/.cihubrc` loading with XDG and project overrides plus `CIHUB_CONFIG` support.
- Added environment overrides for AI keys, Python path, debug, and no-color settings.
- Added first-run setup flow that writes a starter config file.

## 2026-01-19 - Workflow Security & Check Hygiene

### Fix: workflow input hardening (zizmor)

- Route workflow inputs through env variables to avoid template injection in ai-ci-loop, python-ci, and java-ci.
- Annotated release checkout credentials with zizmor suppression for the floating-tag push path.

### Change: local check reliability

- `cihub check` now validates templates via `tests/integration/test_templates.py`.
- `yamllint` ignores legacy templates in `cihub/data/templates/legacy`.
- `isort` skips `.venv` and `cihub-cli/node_modules` during checks.
- `cihub check` now runs against the current working directory when invoked outside the hub repo.

## 2026-01-19 - CLI/Wizard Alignment (Phase 1)

### Fix: Wizard advanced prompts emit schema-valid keys

- Gates now configure `require_run_or_fail` and per-tool defaults instead of non-schema `required/optional`.
- Reports now configure `badges`, `codecov`, `github_summary`, and `retention_days`.
- Notifications now configure `slack` and `email` fields defined in schema.
- Harden-runner now uses `harden_runner.policy` instead of `egress_policy`.

### Change: Schema defaults now fully reflected in defaults/fallbacks

- Added `install.source` and `harden_runner.policy` defaults to generated defaults.
- Added per-tool `require_run_or_fail` defaults for Java/Python tools.

### Change: `cihub init` install default aligns to PyPI

- `--install-from` now defaults to `pypi` (help text and behavior aligned with schema).

### Change: TypeScript CLI respects JSON/runtime support

- TypeScript CLI checks command registry metadata before appending `--json` and blocks interactive-only commands.
- Parent command groups render subcommand help instead of executing.

### Change: Command registry metadata expanded

- `cihub commands list --json` now includes `supports_interactive` and `supports_json_runtime`.

### Change: Report summary commands support JSON

- Added `--json` to `report security-summary`, `report smoke-summary`, `report kyverno-summary`, and `report orchestrator-summary`.

### Change: v1.0 languages constrained to Java/Python

- Schema now limits `language` to `java` and `python` (Node/Go deferred).
- Detection uses the confidence-based language strategies across CLI commands.

## 2026-01-19 - CLI/Wizard Alignment (Phase 5)

### Change: Profile metadata sourced from templates

- Added `_metadata` blocks (description/tools/runtime) to all profile templates.
- Corrected Python fast profile metadata to include `isort`.

### Change: GitHub context reads centralized

- Replaced direct `GITHUB_*` environment lookups with `GitHubContext.from_env()` in report helpers, gates, badges, and release parsing.

### Change: Exit code constants enforced

- Replaced magic exit code numbers with `EXIT_*` constants in command registry, check/smoke summaries, and JSON render status.

## 2026-01-18 - Python CLI AI Enhancement (Phase 1)

### New: Optional AI enhancement in the CLI

- Added `cihub/ai/` module with Claude CLI integration and context builder.
- Added `--ai/--no-ai` flags for `triage`, `check`, and `report` commands.
- Added `CIHUB_AI_PROVIDER` (default: claude) and `CIHUB_DEV_MODE` env vars.
- AI enhancement is optional; missing Claude CLI yields a structured suggestion.

### Change: AI output selection

- `--ai` triggers the AI renderer only for commands with an AI formatter (e.g., `docs stale`), preserving JSON output for other commands.

### Tests

- Added unit tests for the AI module and integration coverage for AI enhancement wiring.

## 2026-01-18 - TypeScript CLI Foundation (Phase 2)

### New: TypeScript CLI scaffolding

- Added `cihub-cli/` project scaffold with `tsconfig.json`, `tsup.config.ts`, and `vitest.config.ts`.
- Added CLI entrypoint and version/health checks against the Python CLI.
- Added initial Vitest coverage for Python CLI version parsing.

## 2026-01-18 - TypeScript CLI Core Components (Phase 3)

### New: Core Ink components

- Added `src/app.tsx` and core UI components (Header, Input, Output, Problems, Suggestions, Table, Spinner, ErrorBoundary).
- Wired the interactive CLI entrypoint to render the Ink app after Python CLI preflight.

## 2026-01-18 - TypeScript CLI Bridge (Phase 4)

### New: Python CLI bridge + parsing

- Added subprocess wrapper, input parser, timeout handling, and error classes.
- Added Zod CommandResult schema and exit code constants.
- Added contract tests for CommandResult payloads.
- Wired the app to execute Python CLI commands and render results.

## 2026-01-18 - TypeScript CLI Slash Commands (Phase 5)

### New: Slash command registry + meta commands

- Added slash command registry with meta command routing and help tables.
- Implemented `/help`, `/clear`, and `/exit` handlers.
- Added mappings for top-level, report, config, docs, adr, and hub-ci subcommands.

## 2026-01-18 - CLI Command Registry (ADR-0059)

### New: CLI command registry for frontends

- Added `cihub commands list --json` to expose CLI command metadata for interactive clients.
- TypeScript CLI now builds its slash registry from the Python CLI command list.

## 2026-01-17 - CLI Workflow Dispatch Watch + Wizard

### New: Dispatch watch + wizard wrapper

- Added `cihub dispatch watch` to poll workflow runs to completion.
- Added `cihub dispatch trigger --watch` for optional post-dispatch tracking.
- Added wizard wrappers for dispatch trigger/watch (no YAML logic).

### Change: Docs audit inventory + guide validation

- Added `cihub docs audit --inventory` for doc inventory counts in JSON output.
- Added guide command validation for `docs/guides/` examples.
- Filtered false positives in plain-text `docs/...` reference scanning.
- Added `scripts/docs_inventory_summary.py` to print inventory counts from `--inventory` output.
- Normalized doc header metadata line breaks (two-space markdown line breaks).

### Change: Command output purity (print-free handlers)

- Removed `print()` usage in command handlers (triage, check, hub config, report summaries, hub-ci helpers, triage watch).
- Hub config and report summary commands now emit output via CommandResult `raw_output`.
- Hub CI config load warnings surface as CommandResult warnings instead of stdout prints.
- `cihub hub-ci command-result` now enforces zero print() calls by default.

### New: Test metrics automation (hub-ci)

- Added `cihub hub-ci test-metrics` to wrap test metrics scripts and README checks.
- Wired `hub-production-ci.yml` to run `cihub hub-ci test-metrics` after mutation tests.
- README drift checks ignore the `Last updated` line to avoid false positives in strict mode.
- Enabled `cihub hub-ci test-metrics --strict` in `hub-production-ci.yml`.

### Tests

- Added dispatch watch coverage and updated CLI parser/command tests.
- Added docs audit coverage for inventory, guide validation, and reference filtering.
- Refreshed CLI help snapshots.
- Added unit coverage for `cihub hub-ci test-metrics`.

## 2026-01-16 - AI CI Loop CLI + Workflow (Internal)

### New: AI CI loop command (internal-only)

- Added `cihub ai-loop` to orchestrate iterative CI + fix loops with triage bundles.
- Supports `--max-iterations`, `--fix-mode`, `--emit-report`, and `--output-dir`.

### Change: AI CI loop remote mode + guardrails (internal-only)

- Added remote loop controls for GitHub Actions polling and triage (`--remote`, `--triage-mode`, `--remote-dry-run`).
- Added push guardrails and branch controls for remote runs (`--push`, `--push-branch`, `--allow-protected-branch`).
- Added contract parsing, artifact pack output, and per-iteration review command (`--contract-file`, `--artifact-pack`, `--review-command`).
- Modularized `ai-loop` internals into focused helper modules.

### New: AI CI loop workflow (internal-only)

- Added `.github/workflows/ai-ci-loop.yml` for `workflow_dispatch` runs that call `cihub ai-loop`.

### Tests

- Added CLI help snapshots for `ai-loop` and updated main help snapshots.

### Docs

- Archived `SYSTEM_INTEGRATION_PLAN.md` and updated references to the archive path.
- Archived `CLEAN_CODE.md` and `remediation.md`; updated references to archive paths.

## 2026-01-16 - Wizard + Aggregation Validation Fixes

### Fix: Wizard repo metadata preservation + subdir detection

- `cihub init` now resolves language using the provided subdir when present.
- Wizard preserves detected repo metadata (for example, `repo.subdir`) instead of dropping it.

### Fix: Java POM warnings align with build tool

- POM warnings skip Gradle repos and keep subdir-aware POM resolution.

### Fix: Report aggregation status reflects gate failures

- Aggregation now accounts for thresholds, require-run tools, and test execution when determining pass/fail.

### Tests

- Added coverage for subdir language detection, Gradle missing POM warnings, aggregation status, and wizard repo preservation.

## 2026-01-16 - Template Alignment for Java Mutation + OWASP

### Fix: Java templates avoid repo-specific mutation targeting

- Gradle templates now leave PITest target classes/tests unset so repos control base package targeting.

### Fix: OWASP NVD key respects CLI config

- `run_owasp` now clears `NVD_API_KEY` when `use_nvd_api_key` is false.

## 2026-01-15 - Schema-Derived Defaults

### Change: Config defaults now schema-derived

- `cihub/data/config/defaults.yaml` and `cihub/config/fallbacks.py` are generated from the config schema.
- `cihub check --audit` now validates defaults.yaml and fallbacks alignment with the schema.
- Added `hub_ci.thresholds.overrides` to allow per-module coverage/mutation targets in hub CI config.

### Docs

- Marked CLEAN_CODE Phase 9.4 (config generation) complete.

## 2026-01-15 - fail_on_* Normalization (Schema/Config Contract)

### New: Canonical fail_on_* helpers

Added normalization layer for consistent access to `fail_on_*` config values:

- `get_fail_on_flag()`: Access boolean fail_on_* flags with schema-aligned defaults
- `get_fail_on_cvss()`: Access CVSS threshold values consistently

### New: Schema-code alignment tests

- Added `tests/test_fail_on_normalization.py` with 53 tests
- Tests verify that code defaults match schema defaults
- Tests validate the canonical mapping and default hierarchy

### Docs

- Added [ADR-0052](../adr/0052-fail-on-flag-normalization.md) documenting the normalization pattern

## 2026-01-15 - Docs Tooling Root Fixes

### Fix: Documentation tooling uses project root

- `cihub docs audit`, `cihub docs stale`, and `cihub docs links` now resolve docs from the project root (not `cihub/data`).
- Workflow reference generation now reads `.github/workflows` from the project root.

### Tests

- Added coverage for R-002 wizard config persistence (`cmd_setup` ↔ `cmd_init`).

## 2026-01-15 - Remediation Wiring Updates

### Fix: Harden-runner wiring and workflow pins

- `config-outputs` emits `run_harden_runner` and `harden_runner_egress_policy` and `hub-ci.yml` forwards them to reusable workflows.
- Caller templates now default to `@v1` and source `hub_ref`/`hub_repo` from repo variables (`HUB_REF`, `HUB_REPO`).

### Fix: Global threshold overrides expanded

- Global `thresholds.*` values now override all supported `max_*` keys in `config-outputs`.

### Fix: Init language alignment

- `cihub init` aligns `repo.language` with the final language and prunes unused language blocks after overrides.

### Fix: Secrets hub repo fallback

- `cihub setup-secrets` requires `--hub-repo` or `CIHUB_HUB_REPO` (hardcoded default removed).

### Fix: Bootstrap installer timeouts

- `scripts/install.py` now applies timeout tiers to git/pip operations.
- Git/local installs require `CIHUB_HUB_REPO` instead of a hardcoded default.

### Fix: Triage UNKNOWN STEP mapping

- Log fallback now cross-references run job metadata to replace `UNKNOWN STEP` entries.

### Fix: Tools reference generation

- `docs/reference/TOOLS.md` is now generated from `cihub/tools/registry.py` via `cihub docs generate`.

### Fix: Template contract verification

- `cihub verify` now accepts dynamic `hub_repo`/`hub_ref` expressions in caller templates when they reference vars/inputs.

### Tests

- Added `config-outputs` coverage for harden-runner outputs and expanded `max_*` overrides.
- Added triage log parser coverage for `UNKNOWN STEP` resolution.

## 2026-01-12 - SYSTEM_INTEGRATION_PLAN Complete (100%)

### Complete: Registry/Wizard/Schema Integration

**SYSTEM_INTEGRATION_PLAN.md** is now 100% complete with all 6 phases finished:

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Schema parity audit | ✅ Complete |
| Phase 1 | Registry threshold normalization | ✅ Complete |
| Phase 2 | Registry bootstrap/sync/diff | ✅ Complete |
| Phase 3 | Wizard profile integration | ✅ Complete |
| Phase 4 | CLI management commands | ✅ Complete |
| Phase 5-6 | Custom tools + command contracts | ✅ Complete |

### Fix: Custom Tool Schema Validation (CRITICAL)

**Problem:** Report schema rejected custom `x-*` tools because `toolStatusMap` had `additionalProperties: false`.  

**Solution:** Added `patternProperties` to allow custom tool keys:

```json
"patternProperties": {
  "^x-[a-zA-Z0-9_-]+$": {
    "description": "Custom tool status (x-* prefix)",
    "type": "boolean"
  }
}
```

**Files changed:**
- `schema/ci-report.v2.json` - Added patternProperties to toolStatusMap definition
- `tests/test_schema_contract.py` - Added 2 new tests for custom tool validation

### New Tests: 159 Tests Across 6 Directories

| Directory | Tests | Purpose |
|-----------|-------|---------|
| `test_repo_shapes/` | 57 | Repo shape matrix (Python/Java × pyproject/setup.py/pom) |
| `test_wizard_flows/` | 37 | CLI/wizard parity, WizardResult, profile selection |
| `test_registry/` | 9 | Registry service (list, diff, sync, bootstrap) |
| `test_config_precedence/` | 8 | deep_merge, tier overrides, tool_enabled |
| `test_schema_validation/` | 13 | Schema structure, customTool, patternProperties |
| `test_custom_tools.py` | 35 | Custom tool execution (Python + Java) |

### Documentation Fixes

- Updated SYSTEM_INTEGRATION_PLAN.md to 100% complete
- Fixed test count inconsistencies (Appendix A.6)
- Clarified Phase 4.1 scope (scoped writes allowed for wizard flows)
- Updated STATUS.md and MASTER_PLAN.md

### Test Suite

- **2707 tests passing** (was 2705)
- Full test matrix verified

## 2026-01-11 - Custom Tools (Phase 6.1)

### New: Custom Tools (x- prefix)

Users can now define custom tools with the `x-` prefix in their config:

```yaml
python:
  tools:
    x-custom-linter:
      enabled: true
      command: "my-lint --check ."
```

**Schema changes:**
- Added `customTool` definition supporting boolean or object with `enabled`, `command`, `fail_on_error`
- Added `patternProperties` with `^x-` pattern to `javaTools` and `pythonTools`

**New helper functions in `cihub/tools/registry.py`:**
- `is_custom_tool(name)` - Check if tool name has x- prefix
- `get_custom_tools_from_config(config, language)` - Extract custom tools
- `get_all_tools_from_config(config, language)` - Get built-in + custom tools
- `is_tool_enabled(config, tool, language)` - Check if any tool is enabled
- `get_custom_tool_command(config, tool, language)` - Get custom tool command

### 2026-01-11 - Bug Fixes for Phase 5.4 and 5.5

### Fixes

**High priority:**
- **Fix:** `repo update --branch` now correctly writes to `default_branch` (schema-compliant) instead of non-schema `branch` field
- **Fix:** `registry sync/diff` suggestions now use proper dict format (`{"message": "..."}`) instead of plain strings - prevents AttributeError in renderer

**Medium priority:**
- **Fix:** `repo update` now validates owner/name dependency per schema - cannot set `--owner` without `--repo-name` (or existing name), and vice versa
- **Fix:** `repo migrate` now uses deep copy to prevent shared nested dict mutation when `--delete-source` is not set
- **Fix:** `threshold get --effective` flag now correctly differentiates between raw overrides and effective (tier-inherited) values
- **Fix:** `threshold set` sparse storage now includes tier profile thresholds in inheritance chain (global → profile → tier config → legacy tier keys)
- **Fix:** Added `--branch` as backward-compatible alias for `--default-branch` to preserve CLI API stability

**Low priority:**
- **Fix:** `threshold set` now implements sparse storage - values matching inherited defaults are not stored as overrides, reducing config noise
- **Fix:** Updated doc comments and SYSTEM_INTEGRATION_PLAN.md to use `--default-branch` as canonical flag

### Tests

- **New:** `tests/test_threshold_cmd.py` - 13 behavior tests covering get/set/list/reset/compare subcommands
- **New:** `tests/test_repo_cmd.py` - 13 behavior tests covering list/show/update/migrate/clone subcommands

## 2026-01-10 - Repo Management Commands (Phase 5.5)

### New: `cihub repo` Command Family

Repository management for registry entries:

| Subcommand | Description |
|------------|-------------|
| `repo list` | List repositories (`--language`, `--tier`, `--with-overrides`) |
| `repo show <name>` | Show detailed repository info (`--effective`) |
| `repo update <name>` | Update metadata (`--owner`, `--default-branch`, `--language`, `--tier`, `--dispatch-enabled`) |
| `repo migrate <from> <to>` | Migrate/rename entry (`--delete-source`, `--force`) |
| `repo clone <source> <dest>` | Clone repository config (`--force`) |
| `repo verify-connectivity <name>` | Verify GitHub access (`--check-workflows`) |

**Note:** `repo update` writes to `config.repo.*` (canonical location) for language, owner, etc.

### 2026-01-10 - Threshold Management Commands (Phase 5.4)

### New: `cihub threshold` Command Family

Complete threshold management for CI quality gates:

| Subcommand | Description |
|------------|-------------|
| `threshold get [<key>]` | Get threshold value(s) (`--repo`, `--tier`, `--effective`) |
| `threshold set <key> <value>` | Set threshold (`--repo`, `--tier`, `--all-repos`) |
| `threshold list` | List all thresholds with descriptions (`--category`, `--diff`) |
| `threshold reset [<key>]` | Reset to default (`--repo`, `--tier`, `--all-repos`) |
| `threshold compare <repo1> <repo2>` | Compare thresholds between repos (`--effective`) |

**Supported threshold categories:**
- **Coverage:** `coverage_min` (70%)
- **Mutation:** `mutation_score_min` (70%)
- **Security:** `max_critical_vulns`, `max_high_vulns`, `max_pip_audit_vulns`, `owasp_cvss_fail`, `trivy_cvss_fail`, `max_semgrep_findings`, `max_spotbugs_bugs` (0 or 7.0)
- **Lint:** `max_ruff_errors`, `max_black_issues`, `max_isort_issues`, `max_checkstyle_errors`, `max_pmd_violations` (0)

### 2026-01-10 - Profile and Tool Management Commands (Phase 5.1, 5.3)

### New: `cihub profile` Command Family

Complete profile management for CI tool enablement presets:

| Subcommand | Description |
|------------|-------------|
| `profile list` | List available profiles (filter by `--language`, `--type`) |
| `profile show <name>` | Show profile details (`--effective` for merged view) |
| `profile create <name>` | Create new profile (`--from-profile`, `--from-repo`, `--language`) |
| `profile edit <name>` | Edit profile (`--enable`, `--disable`, `--set`) |
| `profile delete <name>` | Delete profile (`--force` for built-ins) |
| `profile export <name>` | Export profile to file (`--output`) |
| `profile import <file>` | Import profile from file (`--name`, `--force`) |
| `profile validate <name>` | Validate profile structure (`--strict` fails on warnings) |

### New: `cihub tool` Command Family

Tool management for discovery, enablement, and configuration:

| Subcommand | Description |
|------------|-------------|
| `tool list` | List available tools (filter by `--language`, `--category`, `--repo`) |
| `tool enable <tool>` | Enable tool (`--for-repo`, `--all-repos`, `--profile`) |
| `tool disable <tool>` | Disable tool (`--for-repo`, `--all-repos`, `--profile`) |
| `tool configure <tool> <param> <value>` | Configure tool setting (`--repo`, `--profile`) |
| `tool status` | Show tool status across repos (`--repo`, `--all`) |
| `tool validate <tool>` | Validate tool installation (`--install-if-missing`) |
| `tool info <tool>` | Show detailed tool information |

### Security: Path Traversal Prevention

**Fix:** Profile and tool commands now validate names to prevent path traversal:
- Rejects names containing `/`, `\`, or `..`
- Rejects names starting with `.`
- Allows only alphanumeric, dash, underscore characters

### Registry Service Enhancements

**Fix:** `get_repo_config()` and `list_repos()` now include:
- `language` resolved from `config.repo.language` (canonical, with legacy fallback)
- `config` block for tool management commands

### Tool Command Compatibility

**Fix:** Repo-targeted tool commands now:
- Honor `config.repo.language` when resolving repo language
- Reject mismatched tool/language combinations (e.g., Java tools on Python repos)

### CommandResult Contract Improvements

**Fix:** Consistent contract adherence:
- `problems` field now returns `[]` instead of `None` for empty lists
- Registry-modifying tool commands include `files_modified` field

### 2026-01-10 - Docs Command Refactoring (Part 7.4.4)

### Internal: Split `commands/docs.py` into Package

**Refactored:** Monolithic 858-line docs command split into `commands/docs/` package:

| Module | Functionality | Lines |
|--------|--------------|-------|
| `__init__.py` | Main handlers, exports | 132 |
| `links.py` | Link checking (`_check_internal_links`, `_run_lychee`) | 260 |
| `generate.py` | CLI, config, workflow reference generation | 466 |

**Benefits:**
- Link checking isolated from doc generation
- Easier to test each component in isolation
- Reduced file size for easier navigation

**CLI surface unchanged** - `cihub docs generate/check/links` work identically.

### 2026-01-10 - Hub-CI Parser Refactoring (Part 7.4.3)

### Internal: Split `cli_parsers/hub_ci.py` into Family Modules

**Refactored:** Monolithic 638-line parser file split into `cli_parsers/hub_ci/` package:

| Module | Subcommands | Count |
|--------|-------------|-------|
| `release.py` | actionlint, kyverno, trivy, zizmor, release-*, pytest-summary, summary, enforce | 16 |
| `validation.py` | syntax-check, yamllint, repo-check, source-check, validate-*, verify-*, quarantine-check, enforce-command-result | 11 |
| `security.py` | bandit, pip-audit, security-* | 6 |
| `java_tools.py` | codeql-build, smoke-java-* | 6 |
| `python_tools.py` | ruff, black, mypy, mutmut, coverage-verify | 6 |
| `smoke.py` | smoke-python-* | 4 |
| `badges.py` | badges, badges-commit, outputs | 3 |

**Benefits:**
- Smaller, focused files for each command family
- Reduced churn risk when modifying individual commands
- Easier navigation and testing

**CLI surface unchanged** - all 50 hub-ci subcommands work identically.

### 2026-01-10 - Registry Add/Remove Command Extensions (Phase 5)

### New: `registry add` Flags for Sync-Ready Entries

**New flags:**
- `--owner` - Repository owner (GitHub org/user)
- `--name` - Repository name (defaults to repo argument; requires `--owner`)
- `--language` - Repository language (`java` or `python`)

**Behavior:** When all three flags are provided, `registry sync` can create new config files:
```bash
cihub registry add my-repo --owner my-org --language python --tier standard
cihub registry sync  # Creates config/repos/my-repo.yaml
```

### New: `registry remove` Command

**Usage:**
```bash
cihub registry remove <repo> --yes                # Remove from registry only
cihub registry remove <repo> --yes --delete-config  # Also delete config file
```

**Flags:**
- `--yes` - Skip confirmation prompt (required for non-interactive use)
- `--delete-config` - Also delete `config/repos/<repo>.yaml`

### Registry Import Validation Guards

The `registry import` command now validates input data before persisting:
- Rejects non-dict `repos` or `tiers` values with clear error messages
- `--replace` mode requires complete structure (`schema_version`, `tiers`, `repos`)
- Prevents schema-invalid registries from being persisted

### Breaking: `--name` Now Requires `--owner`

**Reason:** The registry schema enforces `owner`/`name` as both-or-none (`dependencies` constraint). Providing `--name` without `--owner` would create schema-invalid registry entries.

**Error:** `--name requires --owner (schema enforces owner/name as both-or-none)`

### 2026-01-10 - Registry Bootstrap Import + Conflict Audit (Phase 3)

### Update: `cihub registry bootstrap` Import Scope

**Behavior:** Bootstrap now imports registry-managed config fragments from `config/repos/*.yaml`:
- `repo` metadata, `gates`, `reports`, `notifications`, `harden_runner`
- `python`/`java` blocks, `thresholds_profile`, `cihub`, `version`

**Note:** `--include-thresholds` remains opt-in for thresholds; it now stores only overrides that differ from tier + profile defaults.

### Update: Bootstrap Conflict Detection

**Merge strategy now reports conflicts for:**
- Tier mismatches (existing)
- Language mismatches (legacy top-level vs config)
- Managed config fragment differences
- Threshold override differences

### Test Coverage

Expanded bootstrap coverage in `tests/test_registry_cross_root.py`:
- Replace/prefer-config strategy behavior
- Managed fragment import
- Sparse threshold import vs profile defaults
- Managed config fragment conflicts

## 2026-01-09 - JSON Mode Purity + New Hub-CI Commands (CLI Hardening)

### New: JSON Mode Purity for CLI Commands

**Problem:** When commands are invoked with `--json`, auxiliary output (github-format annotations, stdout summaries) pollutes the JSON stream, breaking programmatic consumers.  

**Solution:** Added `json_mode` field to `GitHubContext` that suppresses non-JSON stdout:
- `write_outputs()` skips stdout fallback in JSON mode (use GITHUB_OUTPUT instead)
- `write_summary()` skips stdout fallback in JSON mode (use GITHUB_STEP_SUMMARY instead)
- `cmd_ruff()` skips `--output-format=github` pass in JSON mode

**Test Coverage:**
- New test directory: `tests/test_cli_contracts/`
- JSON purity tests: `tests/test_cli_contracts/test_json_purity.py`

### New: Hub-CI Python Tool Commands

**New commands:**
- `cihub hub-ci yamllint` - Lint YAML files (hub defaults, repo configs, profiles)
- `cihub hub-ci ruff-format` - Run ruff formatter in check mode
- `cihub hub-ci mypy` - Run mypy type checking

**Also:**
- All hub-ci subparsers now accept `--json` flag directly (not only at parent level)
- `--min-mutation-score` is now the canonical arg name (alias: `--min-score`)

### New: Setup Wizard Command (ADR-0051)

**New command:** `cihub setup` - Complete onboarding wizard

**Steps orchestrated:**
1. Project creation (scaffold) OR detection of existing project
2. Configuration file generation (.ci-hub.yml)
3. Workflow file creation (.github/workflows/hub-ci.yml)
4. Configuration validation
5. Local CI run (optional)
6. GitHub setup - repo creation and push (optional)
7. GitHub Actions trigger (optional)

**ADR-0051 (Wizard Profile-First Design):**
- Profiles are presented as starting points, not restrictions
- Users ALWAYS see individual tool checkboxes for customization
- Reduces wizard from 15+ prompts to 3-4 for most users

---

### 2026-01-09 - Registry Schema Normalization + Threshold Resolution (Phase 2.4b)

### Update: Schema-Aligned Threshold Keys

**Problem:** Registry used legacy threshold keys (`coverage`, `mutation`, `vulns_max`) while the schema uses (`coverage_min`, `mutation_score_min`, `max_critical_vulns`, `max_high_vulns`).  

**Solution:** Registry service now normalizes threshold keys on load/save:

| Legacy Key | Schema Key |
|------------|------------|
| `coverage` | `coverage_min` |
| `mutation` | `mutation_score_min` |
| `vulns_max` | `max_critical_vulns`, `max_high_vulns` |

**Backward compatibility:** Legacy keys still accepted, normalized on load.

### Update: Effective Threshold Resolution

**`list_repos()` and `get_repo_config()` now compute effective thresholds from:**
1. Schema defaults (fallback)
2. Profile config (if tier specifies a profile)
3. Tier config fragment (`tiers.<tier>.config.thresholds`)
4. Legacy tier threshold keys (top-level in tier)
5. Repo config fragment (`repos.<repo>.config.thresholds`)
6. Explicit overrides (`repos.<repo>.overrides`)

**New list output fields:**
- `has_threshold_overrides`: True if repo has any per-repo threshold config
- `has_config_thresholds`: True if repo has `config.thresholds` (managedConfig)

### Update: Registry Schema Strictness

- `registry.schema.json` now has `additionalProperties: false` at root
- Added extensive `$defs` for sparse config fragments referencing `ci-hub-config.schema.json`
- Added `managedConfig` definition with allowlisted config keys

### Update: Repo Metadata Normalization

**Problem:** Repo metadata (`language`, `dispatch_enabled`) was duplicated at top-level and in `config.repo`.  

**Solution:** `_normalize_repo_metadata_inplace()` deduplicates when values match; `_compute_repo_metadata_drift()` detects conflicts.

### Test Coverage

New test files:
- `tests/test_registry_cross_root.py` - Hub root derivation for `--configs-dir`
- `tests/test_registry_roundtrip_invariant.py` - Registry write/read preserves values
- `tests/test_registry_schema_contract.py` - Schema contract validation
- `tests/test_registry_service_threshold_mapping.py` - Threshold resolution tests

---

### 2026-01-09 - Registry Sync Applies Managed Config Fragments (Phase 2.3a)

### New: `cihub registry sync` applies tier/repo config fragments

**Behavior:** `cihub registry sync` now merges allowlisted tier/repo config fragments (`tiers.<tier>.config`, `repos.<repo>.config`) into `config/repos/<repo>.yaml` in addition to threshold syncing.

**Notes:**
- Sync merges the tier's `profile` config (if present) plus `tiers.<tier>.config` plus `repos.<repo>.config`.
- Sync does **not** expand `thresholds_profile` (threshold profile presets) yet.
- This is a partial Phase 2.3 step; full “registry owns all hub-managed config” is still pending Phase 2.2/2.4.

**Test Coverage:**
- Sync applies tier fragments: `tests/test_registry_service_threshold_mapping.py::test_sync_to_configs_applies_tier_config_fragments`
- Round-trip via loader: `tests/test_registry_roundtrip_invariant.py`

### Update: `cihub registry diff` surfaces managedConfig drift (Phase 2.4a)

**Behavior:** `cihub registry diff` now reuses the sync engine in dry-run mode to surface drift for allowlisted non-threshold keys (repo/tools/gates/reports/etc), in addition to thresholds drift.

**Also fixed:**
- `--configs-dir` now derives a hub root for registry/profiles/defaults loading, and errors if the hub root cannot be derived or the target `config/registry.json` is missing.
- `--configs-dir` accepts `<hub>/config` and maps it to `<hub>/config/repos`.
- Registry list `*` marker reflects any per-repo threshold config (explicit overrides or managedConfig.thresholds).
- Registry sync applies managed fragments without globally normalizing repo configs (avoids rewriting unrelated keys).
- Fragment normalization skips CVSS fallback injection for sparse fragments (no automatic `trivy_cvss_fail`).

---

## 2026-01-08 - Registry Sparse Config Audit (Phase 2.2a)

### New: Sparse Config Fragment Audit in `cihub registry diff`

**Problem:** Registry config fragments are intended to be sparse, but redundant values can accumulate and hide drift.  

**Solution:** `cihub registry diff` now reports non-sparse config fragment values as `sparse.config.*` warnings for both tier and repo config fragments.

**Test Coverage:**
- New sparse audit tests for tier and repo config fragments in `tests/test_registry_service_threshold_mapping.py`

---

## 2026-01-07 - Triage Command Modularization (ADR-0050)

### Refactor: Triage Command Package (ADR-0050 Phases 1-3)

**Problem:** `triage.py` had grown to 1502 lines handling 8 different responsibilities.  

**Solution:** Modularized into `cihub/commands/triage/` package:

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `triage_cmd.py` | 558 | Main command handler (63% reduction) |
| `types.py` | 116 | Constants, severity maps, filter helpers |
| `github.py` | 313 | GitHubRunClient encapsulating gh CLI |
| `artifacts.py` | 93 | Artifact finding utilities |
| `log_parser.py` | 154 | Log parsing for failures |
| `remote.py` | 376 | Remote bundle generation |
| `verification.py` | 227 | Tool verification |
| `output.py` | 89 | Output formatting helpers |
| `watch.py` | 136 | Watch mode |

**Benefits:**
- Each module has single responsibility
- `GitHubRunClient` class encapsulates all `gh` CLI calls
- Backward compatible via `__init__.py` re-exports
- All 487 tests passing

### Fix: Zizmor Template-Injection Warnings (45→0)

**Files fixed:** All GitHub Actions workflows with template injection vulnerabilities.

**Pattern:** Converted `${{ inputs.* }}` to environment variables:
```yaml
# Before (vulnerable to injection):
run: echo "${{ inputs.value }}"

# After (safe):
env:
 VALUE: ${{ inputs.value }}
run: echo "$VALUE"
```

**Workflows updated:**
- hub-security.yml, smoke-test.yml, hub-production-ci.yml
- kyverno-ci.yml, kyverno-validate.yml, release.yml

### New: `resolve_flag()` CLI Helper

**Location:** `cihub/utils/env.py`

**Purpose:** Unified pattern for CLI flags with environment variable fallback.

**Priority chain:** CLI arg → env var → default

**Usage:**
```python
from cihub.utils.env import resolve_flag

# In command handler:
bin_path = resolve_flag(args.bin, "ZIZMOR_BIN", default="zizmor")
```

**Commands updated:** `repo-check`, `kyverno-validate`, `kyverno-test`, `actionlint`

---

## 2026-01-06 - CLI Re-exports Cleanup (Part 5.1)

### Removed: CLI Re-exports (CLEAN_CODE.md Part 5.1)

**Problem:** `cihub/cli.py` re-exported 50+ functions for backward compat, creating messy dependencies.  

**Solution:** Fixed imports directly instead of phased deprecation:
- Updated ~20 test files to import from canonical locations
- Removed 50+ re-export lines from `cli.py`
- `cli.py` now only exports `main` and `build_parser`

**Import changes:**
- `CommandResult` → `from cihub.types import CommandResult`
- `hub_root`, `get_git_branch`, etc. → `from cihub.utils import ...`
- `render_dispatch_workflow` → `from cihub.services.templates import ...`
- POM utilities → `from cihub.utils import ...`

### Status
- CLEAN_CODE.md: Part 5.1 [x] COMPLETE
- All 2234 tests passing

---

### 2026-01-06 - RunCIOptions Dataclass (Part 3.2)

### New: `RunCIOptions` Dataclass (CLEAN_CODE.md Part 3.2)

**Implementation:**
- Created frozen dataclass `RunCIOptions` in `cihub/services/types.py`
- Consolidates 10 keyword parameters into single immutable object
- Fields: output_dir, report_path, summary_path, workdir, install_deps, no_summary, write_github_summary, correlation_id, config_from_hub, env
- `from_args()` class method for CLI integration
- Updated `run_ci()` to accept optional `options` parameter
- Full backward compatibility: kwargs still work

**Updated Callers:**
- `cihub/commands/ci.py` now uses `RunCIOptions.from_args(args)`

**Test Coverage:**
- 11 tests in `tests/test_services_ci.py` (2 original + 9 new for RunCIOptions)

**Also fixed:**
- Pre-existing import issues with `_get_repo_name` and `_detect_java_project_type`
- Added backward compatibility aliases across modules

### Status
- CLEAN_CODE.md: Part 3.2 [x] COMPLETE
- All 2233 tests passing

---

### 2026-01-06 - Unified GitHubContext (Part 3.1)

### New: Unified `GitHubContext` Class (CLEAN_CODE.md Part 3.1)

**Implementation:**
- Extended `OutputContext` into unified `GitHubContext` class in `cihub/utils/github_context.py`
- Combined environment reading + output writing into single class (per user insight: "two separate things is stupid")
- 11 GitHub env var fields: repository, ref, ref_name, sha, run_id, run_number, actor, event_name, workspace, workflow_ref, token
- `from_env()` class method to read from GITHUB_* environment variables
- `from_args()` class method for CLI output configuration (backward compatible)
- `with_output_config()` to combine env context + output config in one call
- Helper properties: `is_ci`, `owner_repo`, `owner`, `repo`, `short_sha`
- Backward compatibility: `OutputContext = GitHubContext` alias

**Test Coverage:**
- 59 tests in `tests/test_output_context.py` (38 original + 21 new)
- Tests cover from_env, properties, with_output_config, backward compatibility

### Status
- CLEAN_CODE.md: Part 3.1 [x] COMPLETE
- All 2241 tests passing

---

### 2026-01-06 - Subprocess Consolidation (Part 7.3.3)

### New: `safe_run()` Wrapper (CLEAN_CODE.md Part 7.3.3)

**Implementation:**
- Created `cihub/utils/exec_utils.py` with centralized subprocess handling
- Added timeout constants per ADR-0045:
 - `TIMEOUT_QUICK = 30` (simple commands)
 - `TIMEOUT_NETWORK = 120` (network operations)
 - `TIMEOUT_BUILD = 600` (build/test commands)
 - `TIMEOUT_EXTENDED = 900` (long-running operations)
- Custom exceptions: `CommandNotFoundError`, `CommandTimeoutError`
- Consistent UTF-8 encoding and capture_output defaults

**Migration Scope:**
- 34 subprocess.run() calls migrated across 14 files
- Files: triage.py, verify.py, check.py, docs.py, preflight.py, secrets.py, templates.py, release.py, python_tools.py, security.py, io.py, helpers.py, git.py (docs_stale), shared.py, hub_ci/__init__.py

**Test Coverage:**
- 22 new tests in `tests/test_exec_utils.py`
- Hypothesis property-based tests for edge cases
- Updated existing tests to use new monkeypatch targets

### Status
- CLEAN_CODE.md: ~85% → ~90% complete
- All 2220 tests passing

---

### 2026-01-06 - Security Audit + Consistency Fixes

### Security Fixes (CRITICAL)

**ZIP Path Traversal (CVE-2007-4559 variant):**
- Added `_safe_extractall()` helper with `Path.relative_to()` validation
- Fixed in: `cihub/core/correlation.py`, `cihub/core/aggregation/github_api.py`, `scripts/debug_orchestrator.py`
- Pattern: Validate each ZIP member path stays within target directory before extraction

**Tarball Symlink Attack:**
- Added `issym()` and `islnk()` rejection before tarball extraction
- Fixed in: `cihub/commands/hub_ci/__init__.py`
- Pattern: Reject symbolic links and hard links in tarballs

### Consistency Fixes (23 Low Severity Issues)

**Token Environment Variable Priority:**
- Added `get_github_token()` helper to `cihub/utils/env.py`
- Standardized priority: `GH_TOKEN` → `GITHUB_TOKEN` → `HUB_DISPATCH_TOKEN`
- Updated: `templates.py`, `dispatch.py`, `aggregate.py`

**Safe Integer Parsing:**
- Added `env_int()` helper to `cihub/utils/env.py`
- Updated: `release.py` (Trivy env var parsing)

**Exit Code Consistency:**
- `smoke.py` now returns `EXIT_FAILURE` when tests fail (was always SUCCESS)
- Added problem entry with error code `CIHUB-SMOKE-TEST-FAILURE`

**Path Traversal Prevention:**
- Added `validate_subdir()` calls to `init.py`, `new.py`

**Magic Number Constants:**
- Added `MAX_LOG_PREVIEW_CHARS = 2000` to `python_tools.py`
- Added `MAX_ERRORS_IN_TRIAGE = 20` to `triage.py`
- Added `HEALTH_CHECK_INTERVAL_SECONDS = 5` and `HEALTH_CHECK_HTTP_TIMEOUT_SECONDS = 5` to `docker_tools.py`

**Code Consolidation:**
- `get_tool_enabled()` in `config/loader/core.py` now delegates to canonical `tool_enabled()` from `normalize.py`

**API Cleanup:**
- Removed private functions from `__all__` in `utils/__init__.py`: `_parse_env_bool`, `_bar`, `_get_repo_name`, `_detect_java_project_type`
- Updated imports in `gates.py`, `java.py`, `build.py` to use public function names

### Test Updates
- Updated test assertions to match new behavior (2 tests)
- All 2120 tests passing

---

## 2026-01-05 - CommandResult Migration + Test Reorganization Plan

### Code Review Fixes (CLEAN_CODE.md Phase 3)

**Migration Quality Improvements:**
- **detect.py** - Pure CommandResult return (no conditional JSON mode)
- **validate.py** - Added YAML parse error handling (yaml.YAMLError, ValueError)
- **smoke.py** - Fixed TemporaryDirectory resource leak with explicit cleanup
- **discover.py** - Reordered empty check before GITHUB_OUTPUT write
- **cli.py** - Error output now routes to stderr (CLI best practice)

**Test Updates:**
- Updated test patterns: `result.exit_code` instead of comparing `result == int`
- Added `--json` flag to E2E detect tests for proper JSON output
- All 2101+ tests passing

### TEST_REORGANIZATION.md Plan Created

**New Design Doc:** `docs/development/archive/TEST_REORGANIZATION.md`

Comprehensive plan for restructuring 2100+ tests from flat `tests/` into organized hierarchy:
- `tests/unit/` - Fast, isolated, no I/O
- `tests/integration/` - Cross-module, may use filesystem
- `tests/e2e/` - Full workflows, slow
- `tests/contracts/` - Schema/API contract tests
- `tests/property/` - Hypothesis property-based tests
- `tests/regression/` - Bug reproduction tests

**Living Metadata System:**
- Uses existing `config/defaults.yaml` `hub_ci.thresholds` as single source of truth
- Auto-generated test file headers with metrics
- Auto-generated `tests/README.md` with coverage table

### 5-Agent Parallel Audit

Completed comprehensive audit of TEST_REORGANIZATION.md plan identifying critical gaps:

| Aspect | Finding |
|--------|---------|
| Test Structure | 45% of files (35/78) don't fit proposed categories |
| Config Integration | `cihub hub-ci thresholds` CLI command not implemented |
| Schema | Per-module overrides blocked by `additionalProperties: false` |
| Automation | 3 scripts must be written (update_test_metrics, generate_test_readme, check_test_drift) |
| Drift Detection | Only ~20% of scenarios covered |

**Estimated effort:** ~10-12 days before Phase 1 can start

### Documentation Updates
- Updated STATUS.md with current progress and active design docs
- Updated MASTER_PLAN.md with code review fixes and TEST_REORGANIZATION references
- Added TEST_REORGANIZATION.md to Active Design Docs table

---

### 2026-01-05 - v1.0 Cutline + Plan Alignment

### MASTER_PLAN.md Updates
- Added **v1.0 Cutline** section with Quick Wins, Heavy Lifts, and Verification items.
- Created **Post v1.0 Backlog** section for explicitly deferred items:
 - Registry & Versioning (centralized registry CLI, versioning/rollback)
 - Triage Enhancements (schema validation, DORA metrics)
 - Governance (RBAC, approval workflows)
 - Optional Tooling (act integration, Gradle, Docker multi-stage)
 - PyQt6 GUI wrapper (deferred until CLI stabilizes)
- v1.0 Quick Wins: docs stale, docs audit, config validate, audit umbrella, --json everywhere, _tool_enabled consolidation, gate-spec refactor, CI-engine tests.
- v1.0 Heavy Lifts: env/context wrapper, runner/adapter boundaries.

### AGENTS.md Updates
- Updated "Current Focus" to link to MASTER_PLAN.md v1.0 cutline (single source of truth).
- Listed v1.0 Quick Wins in order for immediate reference.
- Removed duplicate/stale "Current Focus" items now covered by MASTER_PLAN.md.
- Extracted CI Parity Map (~50 lines) to `docs/development/CI_PARITY.md`; replaced with summary + link.
- Fixed aspirational claims: CLI output contract now notes hub-ci gaps, workflow install rule consolidated.
- Corrected parity map: verify-matrix-keys uses CLI (not script), license-check is partial match (CI adds --github-summary).

### New Documentation
- **`docs/development/CI_PARITY.md`**: Full CI parity map with Exact/Partial/CI-only/Local-only categories, check tier mapping, and maintenance notes.

### Governance
- Verified design doc references aligned between MASTER_PLAN.md and STATUS.md.
- All active design docs (CLEAN_CODE.md, DOC_AUTOMATION_AUDIT.md, PYQT_PLAN.md) properly referenced.
- Updated STATUS.md directory structure to include CI_PARITY.md.

### 2026-01-05 - Config Loader Canonicalization + CLI Layering

### CLI
- Moved CLI helper imports in commands to services/utils (no CLI surface changes).
- Added a parser builder helper to support docs generation without importing `cihub.cli`.

### Config
- `load_ci_config`/`load_hub_config` now delegate to the canonical validated loader.
- Default config loading falls back to built-in defaults when `defaults.yaml` is empty or missing.
- Preserve repo-local `repo.owner`/`repo.name`/`repo.language` when no hub override exists.
- `load_effective_config` now delegates to the validated loader (schema-enforced).

### Tests
- Added Stage 2 AST boundary enforcement for core/services/commands layering.
- Updated .ci-hub.yml fixtures to include required repo fields and top-level language.

### Documentation
- Consolidated P0/P1/nonfunctional checklists into `docs/development/specs/REQUIREMENTS.md`.
- Archived legacy spec files and updated references to the consolidated requirements.
- Marked `docs/development/research/RESEARCH_LOG.md` as historical reference-only.
- Updated doc index/status to reflect specs and research locations.

## 2026-01-04 - Maintainability Audit (MASTER_PLAN.md §10)

### Audit Findings
- Multi-agent audit of CLI (87 commands), services, workflows, and automation plans.
- Identified 5 implementations of `_tool_enabled()` (54 usages) - consolidation needed.
- `test_services_ci.py` has only 2 tests - major coverage gap.
- `hub-ci` subcommands (47 commands) explicitly block `--json` flag.
- 21 unpinned `step-security/harden-runner` uses in workflows.
- 38+ `if language ==` branches - Language Strategies pattern needed.

### MASTER_PLAN.md Updates
- Added Section 10 (Maintainability Improvements) with CLI-compatible action items.
- All items follow ADR-0031 (CLI-first) - no composite actions or workflow logic.
- Linked to `archive/CLEAN_CODE.md` for Language Strategies design.
- Added 4 new items from second audit pass:
 - Env/context wrapper (`GitHubContext` centralizes 17 `GITHUB_*` reads)
 - Runner/adapter boundaries (subprocess only in `ci_runner/`)
 - Output normalization (forbid `print()` in commands)
 - Performance guardrails + "no inline logic" workflow guard

### Dropped Recommendations
- Composite actions (violates CLI-first architecture).
- Workflow consolidation via modes (adds YAML complexity).
- Typer/pdoc migrations (nice-to-have, not needed).

### 2026-01-04 - Governance Alignment + Doc Automation Backlog

### Documentation Governance
- Expanded MASTER_PLAN.md References section to include all active design docs (CLEAN_CODE.md, DOC_AUTOMATION_AUDIT.md, PYQT_PLAN.md).
- Added Scope Guardrails #5 and #6 for active docs lifecycle (`active/` → `archive/` with superseded header).
- Added Section 6b (Documentation Automation) with full backlog from DOC_AUTOMATION_AUDIT.md design doc.
- Connected Section 9 (Triage/Registry/LLM) to doc freshness tooling via `.cihub/tool-outputs/`.
- Fixed AGENTS.md stale references: `PLAN.md` → `MASTER_PLAN.md` (3 occurrences).

### Documentation Automation Backlog (MASTER_PLAN.md §6b)
- `cihub docs stale`: AST symbol extraction, schema key diffing, CLI surface drift, file move/delete detection.
- `cihub docs audit`: active ↔ STATUS.md sync, archive header validation, plain-text reference scan, ADR metadata lint.
- `.cihub/tool-outputs/` artifacts: `docs_stale.json`, `docs_stale.prompt.md`, `docs_audit.json`.
- Doc manifest (`docs_manifest.json`) for LLM context.
- Generated references expansion: TOOLS.md from registry, WORKFLOWS.md from workflows.

### 2026-01-04 - Doc Lifecycle + ADR Updates

### Documentation
- Created `docs/development/active/` folder for in-flight design docs.
- Moved CLEAN_CODE.md, DOC_AUTOMATION_AUDIT.md, PYQT_PLAN.md to `active/`.
- Updated docs/README.md, MASTER_PLAN.md, STATUS.md with new folder structure.
- Added `cihub docs audit` spec to MASTER_PLAN.md (active ↔ STATUS.md consistency checks).
- Archived `docs/MAKE.md` → `development/archive/MAKE.md`.
- Consolidated Make guidance into GETTING_STARTED.md (pre-push workflow) and DEVELOPMENT.md (config/debug targets).
- Added "Make targets are CLI wrappers" note to both docs.
- Added Make target drift check to `cihub docs audit` spec (verify referenced targets exist in Makefile).

### ADRs
- ADR-0035: Changed Status from Proposed → Accepted; added Implementation Note.
- ADR-0031: Added Enforcement Addendum (what's allowed inline vs must use CLI).
- ADR-0018: Fixed broken link to SMOKE_TEST.md → INTEGRATION_SMOKE_TEST.md.

### 2026-01-04 - Service Boundary + CVSS Split

### CLI
- Moved CI execution core into `cihub.services` with CLI adapter delegation.
- Added Trivy CVSS threshold outputs for workflow inputs.
- Added `cihub hub-ci trivy-install` for workflow-managed Trivy setup.
- Added Docker Compose runner for `run_docker` (optional health check + logs).
- Added `cihub report aggregate --details-output` and `--include-details` for per-repo detail summaries.
- Added `CIHUB_DEBUG` env toggle for opt-in developer tracebacks and debug context.
- Added `CIHUB_VERBOSE` env toggle for streaming tool output plus persisted tool logs.
- Added `CIHUB_DEBUG_CONTEXT` env toggle for opt-in CLI context blocks (ci/report build/aggregate).
- Added `cihub triage` to emit triage bundles (`triage.json`, `priority.json`, `triage.md`, `history.jsonl`).
- Added `CIHUB_EMIT_TRIAGE` env toggle for automatic triage emission after `cihub ci`.

### Config
- Added `thresholds.trivy_cvss_fail` and `python.tools.trivy.fail_on_cvss`.
- Added `python.tools.bandit.fail_on_medium` and `python.tools.bandit.fail_on_low` gates.
- Added hub CI bandit gate toggles (`hub_ci.tools.bandit_fail_high/medium/low`).
- Documented normalize-only config pipeline for workflow input generation.
- Added Python docker config fields (`compose_file`, `health_endpoint`, `health_timeout`) for parity with Java.
- Added `codeql.fail_on_error`, `docker.fail_on_error`, and `docker.fail_on_missing_compose` gates for strict failure control.

### Workflows
- Added `trivy_cvss_fail` input to `python-ci.yml` and passthrough from `hub-ci.yml`.
- Install Trivy in `python-ci.yml`/`java-ci.yml` when `run_trivy` is enabled.
- Wired hub CI bandit severity env toggles into `hub-production-ci.yml`.
- Run CodeQL in `python-ci.yml`/`java-ci.yml` when `run_codeql` is enabled (SARIF upload via CodeQL action).
- `hub-orchestrator.yml` can write and upload `hub-report-details.md` and optionally embed per-repo details in the summary.
- Defaulted `hub-orchestrator.yml` `include_details` to true for manual runs.
- Added workflow inputs/env passthrough for debug/verbose/triage toggles and triage/log artifacts in CI uploads.
- `hub-run-all.yml` installs Trivy and runs CodeQL actions when toggles are enabled, and can emit `hub-report-details.md`.

### Aggregation
- Mark missing report artifacts as `missing_report` so summaries show `MISSING` instead of empty metrics.

### Docs
- Updated ADRs and workflow docs for split CVSS thresholds and services boundary.

## 2026-01-03 - Workflow CLI Consolidation

### CLI
- Added hub workflow helper commands under `cihub hub-ci` (actionlint install/run, syntax checks, repo/source checks, security scans, CodeQL build, Kyverno helpers, smoke-test helpers, release tag helpers).
- Added `cihub hub-ci zizmor-run` to generate SARIF with an empty fallback on failure (no-inline compliance).
- `cihub hub-ci badges` now respects `hub_ci.tools` toggles and emits deterministic `disabled` badges for disabled tools.
- Security helpers now warn and set tool_status when a tool fails without valid output.
- `cihub sync-templates --check/--dry-run` skips gracefully with a warning when no GitHub token is available.
- Added services layer wrappers for CI runs, config helpers, and report summaries (`cihub.services.*`).
- Added `scripts/cli_command_matrix.py` to list/run guide-aligned CLI command checks.

### Config
- Allow shorthand booleans for tool configs and normalize at load boundaries to preserve defaults.
- Consolidated config loader I/O/merge to shared utilities.
- Added `thresholds_profile` presets with explicit overrides via `thresholds`.
- Expanded shorthand booleans to enabled sections (reports, notifications, kyverno, optional features, hub_ci).

### Workflows
- Removed all multi-line `run: |` blocks; workflows now call CLI helpers for logic.
- hub-security, smoke-test, kyverno, release, and hub-production workflow steps now delegate parsing/validation to CLI commands.
- Simplified python-ci/java-ci workflow headers to point at generated CONFIG docs.
- `hub-run-all.yml` summary job now honors `CIHUB_WRITE_GITHUB_SUMMARY`.
- `hub-production-ci.yml` pins actionlint to v1.7.4 for deterministic runs.

### Docs
- Config reference now renders shorthand tool types as `boolean|object`.
- Updated ADRs and guides for service-layer APIs and command-matrix validation.

## 2026-01-02 - Java SBOM Support

### CLI
- Added `java.tools.sbom` support in config loading and report summaries.
- Added syft-based SBOM generation in `cihub ci` (format configurable).
- `cihub hub-ci badges` now runs natively (no scripts dependency).
- Added `cihub hub-ci badges-commit` to commit badge updates (no-inline workflow compliance).
- `cihub ci` warns when reserved optional feature toggles are enabled.
- `cihub ci` can read notification env-var names from config (secrets still in env).
- `cihub report summary` only prints to stdout when `--write-github-summary` is enabled or an output path is provided.

### Config
- Added defaults for `repo.dispatch_enabled`, `repo.force_all_tools`, and `python.tools.sbom.enabled`.
- Added notification env-var name fields for Slack/email settings.

### Docs
- Updated guides and Makefile targets to use CLI replacements for deprecated scripts.

### Workflows
- **hub-ci.yml** now passes `run_sbom` to Java jobs.
- **java-ci.yml** accepts `run_sbom` and wires `CIHUB_RUN_SBOM`.
- **hub-production-ci.yml** gates jobs via `cihub hub-ci outputs` and uses hub-ci thresholds for coverage/mutation.
- **hub-production-ci.yml** generates and commits badges via CLI commands (no inline shell).

## 2026-01-01 - Summary Commands + Snapshot Tests

### CLI
- Added `cihub report security-summary` (modes: repo, zap, overall) for hub-security.yml summaries.
- Added `cihub report smoke-summary` (modes: repo, overall) for smoke-test.yml summaries.
- Added `cihub report kyverno-summary` for kyverno-ci.yml and kyverno-validate.yml summaries.
- Added `cihub report orchestrator-summary` (modes: load-config, trigger-record) for hub-orchestrator.yml summaries.
- All summary commands honor `CIHUB_WRITE_GITHUB_SUMMARY` env var and `--write-github-summary`/`--no-write-github-summary` flags.
- Summary commands no longer print to stdout when the summary toggle disables output.

### Tests
- Added `tests/test_summary_commands.py` with 19 snapshot tests covering all summary commands.
- Tests verify output format parity with old inline heredocs.
- Added toggle audit tests verifying `CIHUB_WRITE_GITHUB_SUMMARY` env var behavior.

### Workflows
- **hub-security.yml**: Replaced inline matrix build with `cihub discover`, replaced inline summaries with CLI commands.
- **smoke-test.yml**: Replaced inline summaries with `cihub report smoke-summary`.
- **kyverno-ci.yml** and **kyverno-validate.yml**: Replaced inline summaries with `cihub report kyverno-summary`.
- **hub-orchestrator.yml**: Replaced inline summaries with `cihub report orchestrator-summary`.
- All workflows now use `CIHUB_WRITE_GITHUB_SUMMARY` env var for toggle control.

### 2026-01-01 - No-Inline Workflow Cleanup

### CLI
- Added `cihub dispatch trigger` to dispatch workflows and poll for run ID (replaces inline JS in hub-orchestrator.yml).
- Added `cihub dispatch metadata` to generate dispatch metadata JSON files (replaces heredoc in hub-orchestrator.yml).
- Added `cihub report dashboard` to generate HTML or JSON dashboards from aggregated reports.
- Added CLI env overrides for tool toggles (e.g., `CIHUB_RUN_PYTEST=true`) and summary toggle (`CIHUB_WRITE_GITHUB_SUMMARY=false`).

### Workflows
- **hub-orchestrator.yml**: Removed 90+ lines of inline JavaScript, now uses `cihub dispatch trigger` and `cihub dispatch metadata`.
- **config-validate.yml**: Updated to use `cihub hub-ci validate-configs` and `cihub hub-ci validate-profiles`.
- **python-ci.yml**: Fixed typo in artifact name (`arme tifact_prefix` → `artifact_prefix`).

### Scripts (Deprecated)
- Removed legacy aggregate_reports shim → use `cihub report dashboard`.

### Tests
- Updated `test_aggregate_reports.py` to import from `cihub.commands.report` instead of deprecated shim.
- Tests now use 3-tuple return (reports, skipped, warnings) matching new API.

## 2025-12-31 - Phase 4: Remaining Scripts → CLI

### CLI
- Added `cihub config apply-profile --profile <path>` to apply profile defaults to repo configs.
- `cihub config apply-profile` now supports `--target` and `--output` for arbitrary file paths (parity with deprecated script).
- Added `cihub hub-ci verify-matrix-keys` to verify hub-run-all.yml matrix references match discover.py output.
- Added `cihub hub-ci quarantine-check [--path <dir>]` to fail if any file imports from `_quarantine`.

### Scripts (Deprecated)
- Removed legacy apply_profile shim → use `cihub config apply-profile`.
- Removed legacy verify-matrix-keys shim → use `cihub hub-ci verify-matrix-keys`.
- Removed legacy quarantine-check shim → use `cihub hub-ci quarantine-check`.

### Workflows
- Updated `hub-production-ci.yml` to use CLI commands instead of deprecated scripts.

### Tests
- Updated `test_apply_profile.py` and `test_templates.py` to import from `cihub.config.merge` and `cihub.config.io` instead of deprecated shims.

### 2025-12-31 - Badge CLI Integration

### CLI
- Added `cihub hub-ci badges` to generate or validate badge JSON from workflow artifacts.

### 2025-12-31 - Summary Toggle + Report Validation Consolidation

### CLI
- `cihub ci` now defaults `GITHUB_STEP_SUMMARY` behavior from `reports.github_summary.enabled` and supports `--no-write-github-summary`.
- `cihub report validate` now accepts `--summary`, `--reports-dir`, and `--debug` for summary/artifact cross-checks.

### Workflows
- `hub-ci.yml` now passes `write_github_summary` to language workflows.
- `python-ci.yml` and `java-ci.yml` pass `--write-github-summary`/`--no-write-github-summary` based on inputs.

### Scripts
- Replaced legacy validate_summary shim with `cihub report validate`.

### 2025-12-31 - Hub Aggregation Moved Into CLI

### CLI
- Added `cihub report aggregate` for hub orchestrator aggregation.
- Added `cihub report aggregate --reports-dir` for hub-run-all aggregation without GitHub API access.
- Removed legacy run_aggregation shim (use `cihub report aggregate`).

### Workflows
- `hub-orchestrator.yml` now calls `python -m cihub report aggregate` instead of inline Python.

### 2025-12-31 - Workflow Contract Verification

### CLI
- Added `cihub verify` to validate caller templates and reusable workflow inputs match.
- `make verify` now runs the contract check before syncing templates.
- Added `cihub verify --remote` (template drift via GitHub API) and `--integration` (clone + run `cihub ci`).
- Added `make verify-integration` for a full integration sweep.

### Tests
- Added workflow contract tests to prevent template/workflow drift.

### 2025-12-31 - Workflow Security & Verification Fixes

### Security
- **Fixed template-injection vulnerabilities in workflows** - Converted `${{ inputs.* }}` to environment variables in `python-ci.yml`, `java-ci.yml`, and `kyverno-ci.yml` to prevent potential command injection.
- **Enhanced zizmor CLI handler** - Added `_run_zizmor()` function in `check.py` with:
 - `--min-severity high` filtering (mirrors bandit pattern)
 - Auto-fix detection with helpful suggestions
 - Direct link to remediation docs

### Bug Fixes
- **Fixed smoke --full test failure** - Added `pythonpath = ["."]` to scaffold template `pyproject.toml` so pytest can find local modules.
- **Fixed gitleaks false positives** - Updated `.gitleaksignore` with correct fingerprints for test file API key patterns.
- **Fixed broken docs links** - Updated sigstore URLs in `KYVERNO.md` and `ADR-0012` (old `/cosign/keyless/` → `/cosign/signing/overview/`).

### CLI Improvements
- `cihub check` now displays suggestions with emoji for failed checks that have remediation guidance.

### 2025-12-31 - Pre-push Verify + Tool Installation

### Developer Workflow
- Added `make verify` to run full pre-push validation (`cihub check --all --install-missing --require-optional`) plus template drift check.
- Added `--install-missing` and `--require-optional` flags to `cihub check` to prompt for installing optional tools and fail if they are missing.
- Added `zizmor` to dev dependencies for local workflow security scanning.
- Fixed smoke validation by adding `thresholds.max_*` fields to the schema and ensuring CI tool execution prefers the active venv.

## 2025-12-30 - Formatter Unification (Ruff-only)

### Breaking Changes
- **Removed Black from `cihub check`** - Ruff format is now the single source of truth for local formatting

### Rationale
- Eliminates formatter conflicts (Ruff and Black can disagree on edge cases)
- Faster formatting (Ruff is 10-100x faster than Black, written in Rust)
- Unified tooling: Ruff handles both linting and formatting

### Notes
- CI workflows still run Black until `hub-production-ci.yml` is updated.
- `cihub check` now invokes mypy/pytest via the current Python interpreter to honor the active environment.

### Migration
- Run `make format` (or `ruff format cihub/ tests/ scripts/`) to format code
- Keep Black installed if CI still enforces it.

### 2025-12-30 - Template Freshness Guard

### Templates & Tests
- Archived legacy dispatch templates to `templates/legacy/`
- Updated docs/tests to reference caller templates under `templates/repo/`
- Added a guard to prevent legacy dispatch templates from drifting in active paths
- Added `.yamllint` config to align linting with 120-char line length and ignore archived templates

### 2025-12-30 - CLI Doc Drift Guardrails & Plan Consolidation

### CLI & Tooling
- Added `cihub docs generate/check` to auto-generate reference docs from CLI and schema.
- Added CLI helpers for local verification: `preflight`/`doctor`, `scaffold`, and `smoke`.
- Added `cihub check` to run the full local validation suite (lint, typecheck, tests, actionlint, docs drift, smoke).
- Added tests for new CLI commands (docs/preflight/scaffold/smoke/check).
- Added pre-commit hooks for actionlint, zizmor, and lychee link checking.

### Documentation & Governance
- Added canonical plan: `docs/development/MASTER_PLAN.md`.
- Added reference-only banners to `pyqt/planqt.md` and archived `docs/development/archive/ARCHITECTURE_PLAN.md`.
- Updated ADRs to reflect `hub-ci.yml` wrapper and CLI-first verification.
- Refreshed `docs/development/status/STATUS.md`.
- Rewrote the audit ledger as `docs/development/archive/audit.md`.
- Generated `docs/reference/CLI.md` and `docs/reference/CONFIG.md` from code.

## 2025-12-26 - Security Hardening & Boolean Config Fix

### Security Fixes (OWASP Audit)
- **H1: GitHub Actions Expression Injection** - Fixed in `hub-orchestrator.yml` by passing matrix values through environment variables instead of direct `${{ }}` interpolation in JavaScript
- **H2: XXE Vulnerability** - Added `defusedxml` dependency for safe XML parsing in CLI POM detection
- **H3: Path Traversal** - Added `validate_repo_path()` and `validate_subdir()` functions in `cihub/cli.py`
- **H6: Force Push Confirmation** - Added interactive confirmation for v1 tag force-push in `cihub sync-templates --update-tag`
- **M3: Subdir Path Traversal** - Added `..` detection in `hub-run-all.yml` before cd into subdir
- **Shell Injection** - Fixed `hub-security.yml` to pass `inputs.repos` via environment variable

### Boolean Config Type Coercion Fix
- **Fixed summary table "Ran" column** - `java-ci.yml` lines 582-590 now use boolean comparison (`== true`) instead of string comparison (`== 'true'`)
- **Added ADR-0028** - Documents boolean type coercion through YAML → Python → GITHUB_OUTPUT → JavaScript → workflow_dispatch → workflow inputs

### Documentation
- Updated ADR README with ADRs 0023-0028
- Added ADR-0028: Boolean Config Type Coercion

### 2025-12-26 - Workflow Shellcheck Cleanup

### Workflows
- Refactored summary output blocks to avoid shellcheck SC2129 warnings across hub workflows.
- Grouped multi-line `GITHUB_OUTPUT` writes to prevent shellcheck parse errors.
- Cleaned up summary generation redirections in hub, security, smoke test, and kyverno workflows.

### 2025-12-26 - Docs Reorg, Fixtures Expansion, CLI Hardening

### Documentation & Governance
- Reorganized development docs into status/architecture/execution/research/archive subfolders.
- Renamed and aligned plan docs to `ARCHITECTURE_PLAN.md` (now archived) and `STATUS.md`.
- Folded fixtures plan into smoke test guide; archived legacy plans and snapshots.
- Refreshed root README and added .github/CONTRIBUTING.md, .github/SECURITY.md, .github/CODE_OF_CONDUCT.md.
- Updated doc indexes and references after reorg.
- Added root Makefile + command matrix for consistent developer workflows.
- Moved CHANGELOG/BACKLOG/DEVELOPMENT into `docs/development/` to reduce root clutter.

### Fixtures & Integration
- Expanded fixture configs (gradle, setup.py, monorepo, src-layout) and added heavy-tool fixtures.
- Added CLI integration runner and updated smoke test guide with the full fixture matrix.

### CLI & Config
- Hardened config merging and profile loading; wizard cancellation handling.
- Normalized CLI output and moved config helpers out of cli.py.
- Config commands now reject unknown tools per language and keep YAML output clean (status to stderr).

### Workflows & CI
- Fixed shell usage in workflows and heredoc usage in python-ci.yml.
- Pinned zizmor install and aligned CI ignore patterns for coverage artifacts.
- Java CI summary now compares boolean inputs correctly.

### Testing
- Added targeted tests for POM parsing, secrets setup, and config command behavior.

## 2025-12-25 - Hub Production CI & Security Hardening

### Workflow Rename
- **Renamed `hub-self-check.yml` → `hub-production-ci.yml`** - Comprehensive production-grade CI for the hub itself

### CLI Config & Wizard Foundations
- Added schema loader/validator in `cihub/config/schema.py` and wired CLI validation to it
- Added wizard scaffolding (styles, validators, questions, summary, core runner)
- Extracted CLI command handlers into `cihub/commands/*` and added wrappers in `cihub/cli.py`
- Added new hub-side commands: `cihub new` and `cihub config` (edit/show/set/enable/disable)
- Updated NEW_PLAN acceptance checklist to require explicit CI summaries and failure context
- Added ADR-0027 documenting hub production CI policy

### Security Hardening
- All GitHub Actions pinned to SHA (supply chain security)
- Added `harden-runner` to all jobs (egress monitoring)
- Added least-privilege `GITHUB_TOKEN` permissions per job
- Trivy pinned to v0.31.0 (was @master)
- Fixed syntax check to properly validate all `cihub/**/*.py` files
- Pinned CodeQL actions to v4 SHA in hub/security/reusable workflows

### New CI Stages
- **Stage 0: Workflow Security** - actionlint + zizmor for workflow validation
- **Stage 5: Supply Chain** - OpenSSF Scorecard + Dependency Review
- SARIF uploads for Trivy, zizmor, and Scorecard findings
- Updated CI summary table with check descriptions and explicit results
- Forced ruff to respect exclusions in CI (skips `_quarantine`)
- Pip-audit now scans requirements files (avoids editable package false positives)

### Documentation
- Updated README and WORKFLOWS.md to reference `hub-production-ci.yml`
- Added Elastic License 2.0

## 2025-12-24 - ADR-0024 Threshold Resolution

### Reusable Workflows
- Removed `threshold_overrides_yaml`; thresholds now resolve from `.ci-hub.yml` and hub defaults via the CLI (config-only).
- Exported effective thresholds (`eff_*`) and wired all gates/summaries to use them (coverage, mutation, OWASP/Trivy, Semgrep, PMD, lint).
- Updated Java `report.json` to emit effective thresholds instead of raw inputs; summaries now show effective values.

### Orchestrator / Contract
- Kept dispatch inputs minimal; thresholds flow from config only per ADR-0024.
- Added ADR-0024 (`docs/adr/0024-workflow-dispatch-input-limit.md`) to document the 25-input limit strategy and single-override approach.

### Caller Templates
- Templates aligned with simplified callers; no `threshold_overrides_yaml` input required.

### 2025-12-24 - Quarantine System, NEW_PLAN, and CLI/Validation Hardening

### Architecture & Governance
- Added `_quarantine/` with phased graduation, `INTEGRATION_STATUS.md`, and `cihub hub-ci quarantine-check` guardrail to prevent premature imports.
- Added `docs/development/archive/ARCHITECTURE_PLAN.md` (proposed self-validating CLI + manifest architecture); noted current blockers in the plan.

### CLI & Validation
- Added `setup-nvd` command; hardened `setup-secrets` token handling and cross-repo verification.
- Added template sync command/guard; validator fixes for summary drift and matrix key validation; wired Java POM checks into `cihub init`.
- Added CLI integration tests and correlation tests.

### Workflows & OWASP/NVD
- Fixed NVD/OWASP handling (use_nvd_api_key toggle, pass tokens) in central/reusable workflows; cleaned up workflow errors (duplicate keys, NameError).
- Note: the `setup-nvd`/NVD integration script still needs a follow-up fix; current version may not work end-to-end.

### Templates/Docs/Schema
- Updated caller templates and docs (TOOLS, WORKFLOWS, CONFIG.md) alongside ADR updates; minor schema/report tweaks to match governance changes.

## 2025-12-23 - CLI Dispatch Token Handling

### CLI (cihub)
- Trim whitespace from PAT input and reject tokens that contain embedded whitespace
- `setup-secrets` now sends the raw token to `gh` (no trailing newline)
- Added optional `--verify` preflight to confirm token validity before setting secrets

## 2025-12-19 - Property-Based Testing Support

### Hypothesis (Python)
- **New `run_hypothesis` input** (boolean, default: `true`) - Enable Hypothesis property-based testing
- **Pass/fail gate** - Property tests fail the build if any test fails
- **Example count tracking** - Shows "Hypothesis Examples: N" in Build Summary
- **Installed automatically** - `hypothesis` package added when running pytest

### jqwik (Java)
- **New `run_jqwik` input** (boolean, default: `false`) - Enable jqwik property-based testing
- **Integrated with Maven** - jqwik tests run via JUnit 5 during normal test phase
- **Property test count tracking** - Shows "jqwik Property Tests: N" in Build Summary
- **Pass/fail gate** - Property test failures fail the Maven build

### Template Updates
- Both `hub-python-ci.yml` and `hub-java-ci.yml` caller templates updated with matching inputs
- Pushed to `ci-cd-hub-fixtures` and `java-spring-tutorials` repos

### Docker Inputs Removed from CI Templates
- **Removed from workflow_dispatch**: `run_docker`, `docker_compose_file`, `docker_health_endpoint`
- **Reason**: GitHub limits workflow_dispatch to 25 inputs; Docker testing is a separate concern
- **Future**: Separate `hub-java-docker.yml` and `hub-python-docker.yml` templates planned
- **Note**: Trivy scanning (`run_trivy`) still works - it doesn't require Docker inputs
- **Reusable workflows still accept these inputs** - repos can hardcode in `with:` block if needed

---

### 2025-12-19 - Job Summary Improvements & Multi-Module Support

### Configuration Summary
- **Configuration Summary at top of job output** - Shows all enabled tools, thresholds, and environment settings at a glance
- **Project type detection** - Shows "Single module" or "Multi-module (N modules)" for Java projects
- **Workdir display** - Shows `. (repo root)` when workdir is "."

### Multi-Module Maven Support
- **JaCoCo aggregation** - Automatically finds and aggregates coverage from all modules' `jacoco.xml` files
- **PITest aggregation** - Automatically finds and aggregates mutation scores from all modules' `mutations.xml` files
- **Per-module breakdown** - Shows coverage/mutation score for each module (only when >1 module)
- **Backwards compatible** - Single-module projects work unchanged

### Lint Summary Improvements
- **Consistent table format** - All tools show in markdown table with Status/Issues/Max Allowed columns
- **Disabled reason shown** - When a tool is disabled, shows why (e.g., `run_ruff=false`)
- **Fixed empty values** - All values default to 0 to prevent display issues

### Mutation Testing Fixes (Python)
- **mutmut 3.x compatibility** - Fixed deprecated CLI options (`--paths-to-mutate`, `--runner`)
- **Result parsing** - Parse emoji output ( = killed, = survived) instead of `mutmut results`
- **Auto config** - Creates temp `setup.cfg` with mutmut config if not present

### New Java Inputs
- Added `max_checkstyle_errors` threshold
- Added `max_spotbugs_bugs` threshold
- Updated caller templates to include new inputs

---

## 2025-12-18 - Schema 2.0 & Reusable Workflow Migration

### Schema 2.0 Report Format
- **Aggregator upgraded for schema 2.0** - Now extracts `tool_metrics`, `tools_ran`, and `tests_passed`/`tests_failed` from reports
- **Added `--schema-mode` flag** - Supports `warn` (default, includes all reports with warning) and `strict` (skips non-2.0 reports, exits 1 if any skipped)
- **New helper functions** - `detect_language()` detects Java/Python from report fields, `get_status()` handles both build/test status fields
- **HTML dashboard enhanced** - Added Language and Tests columns to repository table
- **Comprehensive test coverage** - 28 tests covering helpers, load_reports modes, summary generation, and HTML output

### Orchestrator Migration
- **Dispatch defaults changed to hub-*-ci.yml** - Orchestrator now defaults to reusable workflow callers (`hub-python-ci.yml`/`hub-java-ci.yml`)
- **All repo configs updated** - Explicit `dispatch_workflow` field in all configs (fixtures use new callers, smoke-tests/bst-demo/java-spring use old names until migrated)

### New Files
- `scripts/validate_report.sh` - Bash script for validating report.json against schema 2.0 requirements
- `docs/adr/0019-report-validation-policy.md` - ADR documenting fixture validation strategy (passing vs failing, expect-clean)
- `docs/adr/0020-schema-backward-compatibility.md` - ADR documenting schema migration strategy and --schema-mode flag

### Unreleased (from CHANGES.md)
- Replaced `hub-run-all.yml` matrix builder with CLI config outputs to honor `run_group`, dispatch toggles, and all tool flags/thresholds from schema-validated configs
- Added `cihub hub-ci verify-matrix-keys` to fail fast when workflows reference matrix keys that the builder does not emit
- Hardened reusable workflows: Java/Python CI now enforce coverage, mutation, dependency, SAST, and formatting gates based on run_* flags and threshold inputs
- Stabilized smoke test verifier script (no early exit, no eval) and anchored checks for workflow/config presence
- Added `hub-self-check` workflow (matrix verifier, smoke setup check, matrix dry-run) and unit tests for config loading/generation
- Installed `jq` in reusable workflows and reordered gates to upload artifacts even when enforcement fails

---

## 2025-12-15 (Night)

### Bug Fixes
- **Fixed PITest mutation score showing 0%** - PITest XML uses single quotes (`status='KILLED'`) but grep patterns were looking for double quotes (`status="KILLED"`). Updated regex to match both quote styles: `grep -cE "status=['\"]KILLED['\"]"`
- **Fixed PITest module detection** - Now skips `template` directories that have pom.xml with pitest but aren't actual Maven modules
- **Added debug output** for mutation aggregation to show which mutations.xml files are found and their scores
- Fixed in: `hub-run-all.yml`, `java-ci.yml`, `java-ci-dispatch.yml` (template and fixtures)

### Repository Cleanup
- Added `artifacts/` to `.gitignore` and removed from git tracking
- Added `hub-fixtures/` and `ci-cd-hub-fixtures/` to `.gitignore` (cloned fixture repos)

---

### 2025-12-15 (Evening)

### Bug Fixes
- Fixed SpotBugs, Checkstyle, PMD not running on repos without `mvnw` - added `mvn` fallback
- Fixed mutmut 0% mutation score - tools now properly detect mutations

### Hub Self-Check Workflow
- Added `hub-self-check.yml` workflow that runs on push/PR to validate hub integrity
- Jobs: syntax-check, unit-tests, validate-templates, validate-configs, verify-matrix-keys
- Runs automatically when scripts, tests, templates, config, or schema files change

### Test Coverage
- Added `tests/test_templates.py` with 70 tests validating all templates against schema
- Tests verify profile merging, dispatch template validity, and no stale repo name references
- Total test count: 109 (39 original + 70 new)

### Tool Defaults
- Enabled ALL tools by default in Java dispatch template (pitest, semgrep, trivy, codeql)
- Enabled ALL tools by default in Python dispatch template (mypy, mutmut, semgrep, trivy, codeql)
- Updated fixture dispatch workflows to match with comprehensive tool status in summaries

### Fixture Enhancements
- Added `requirements.txt` to Python fixtures for pip-audit scanning
- Updated workflow summaries to show all 12 tools with status indicators ([x] Ran / [ ] Skipped)
- Temporarily disabled contact-suite-spring config (900 tests, too slow for testing)

### Cross-Repo Authentication
- Added HUB_DISPATCH_TOKEN support for downloading artifacts from dispatched workflow runs
- Required for orchestrator to aggregate reports across repositories

---

### 2025-12-15

### Repository Rename
- Renamed repository from `ci-hub-orchestrator` to `ci-cd-hub`
- Updated all workflow files, documentation, and scripts with new repo name
- Updated git remote URLs and documentation cross-references

### Fixture Enhancement (Comprehensive Tool Testing)
- Enhanced all Python fixtures (`python-passing`, `python-failing`) with rich, mutable code including 20+ math functions with conditionals, loops, type hints
- Enhanced all Java fixtures (`java-passing`, `java-failing`) with comprehensive Calculator classes
- Enabled ALL tools in fixture configs: pytest, ruff, black, isort, bandit, pip-audit, mypy, mutmut, hypothesis, semgrep (Python); checkstyle, spotbugs, owasp, pmd, pitest, semgrep (Java)
- Added intentional bugs and security issues to `*-failing` fixtures for tool detection validation

### Mutmut 3.x Compatibility
- Fixed mutmut invocation for 3.x CLI (removed deprecated `--paths-to-mutate` and `--runner` flags)
- Added `[tool.mutmut]` configuration to fixture `pyproject.toml` files with `paths_to_mutate` and `tests_dir` settings
- mutmut 3.x now uses config file instead of command-line arguments

### Workflow Improvements
- Fixed "Invalid format" errors in GitHub Actions output parsing
- Replaced `grep ... || echo 0` patterns with `${VAR:-0}` default value fallbacks
- Used lookahead regex patterns (`\d+(?= passed)`) for more robust test count extraction
- Added `tail -1` to ensure only final summary line is captured

### Documentation Cleanup
- Removed stale `docs/analysis/scalability.md` (old brainstorm doc)
- Fixed duplicate Kyverno entries in `docs/README.md`
- Added `docs/development/audit.md` to `.gitignore`

## 2025-12-14
- Added docs/development/specs/ with P0, P1, and nonfunctional checklists.
- Replaced STATUS.md with a concise execution checklist linking to requirements.
- Added doc stubs extracted from the old plan: WORKFLOWS, CONFIG.md, TOOLS, TEMPLATES, MODES, TROUBLESHOOTING, ADR index.
- Updated AGENTS to reflect current focus on P0 execution.
- Linked ROADMAP to requirements and noted planned phases.
- Hardened `hub-orchestrator.yml`: pass computed inputs, honor `default_branch`, set dispatch permissions, attempt run-id capture, emit dispatch metadata artifacts, and generate a hub summary/report from dispatch results.
- Added schema validation in orchestrator config load (jsonschema) to fail fast on bad repo configs; compiled scripts to ensure Python syntax.
- Captured dispatch metadata as artifacts for downstream aggregation; summaries now include per-repo dispatch info.
- Implemented aggregation pass to poll dispatched runs, fail on missing/failed runs, download `ci-report` artifacts when present, and roll up coverage/mutation into `hub-report.json`.
- Added schema validation to the config loader and added `jsonschema` dependency to `pyproject.toml`.
- Added copy/paste templates: `templates/repo/.ci-hub.yml` and `templates/hub/config/repos/repo-template.yaml`.
- Added `config-validate` workflow to run schema validation on config/schema changes and PRs.
- Added ADR-0001 (Central vs Distributed) and expanded docs (CONFIG.md, TOOLS, MODES, TROUBLESHOOTING, TEMPLATES).
- Fixed orchestrator config validation indentation bug and added dispatch run-id polling backoff/timeout.
- Added ADRs 0002-0005 (config precedence, reusable vs dispatch, aggregation, dashboard).
- Rewrote ADRs 0003-0006 to match actual implementation: ADR-0003 now accurately documents github-script dispatch mechanism; ADR-0004 now shows actual hub-report.json schema (runs[] array, not object); ADR-0005 added for Dashboard Approach (GitHub Pages); ADR-0006 added for Quality Gates and Thresholds.
