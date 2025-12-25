# Changelog

All notable changes to this project will be documented in this file.

## 2025-12-24 - ADR-0024 Threshold Resolution

### Reusable Workflows
- Added `threshold_overrides_yaml` input to `java-ci.yml` and `python-ci.yml`; thresholds now resolve in order: override YAML → `.ci-hub.yml` → input defaults.
- Exported effective thresholds (`eff_*`) and wired all gates/summaries to use them (coverage, mutation, OWASP/Trivy, Semgrep, PMD, lint).
- Updated Java `report.json` to emit effective thresholds instead of raw inputs; summaries now show effective values.

### Orchestrator / Contract
- Kept dispatch inputs to booleans only; thresholds flow from config/override per ADR-0024.
- Added ADR-0024 (`docs/adr/0024-workflow-dispatch-input-limit.md`) to document the 25-input limit strategy and single-override approach.

### Caller Templates
- Templates adjusted for threshold/input cleanup (pending final sync); templates still need the `threshold_overrides_yaml` input added and synced via `cihub sync-templates`.

## 2025-12-24 - Quarantine System, NEW_PLAN, and CLI/Validation Hardening

### Architecture & Governance
- Added `_quarantine/` with phased graduation, `INTEGRATION_STATUS.md`, and `check_quarantine_imports.py` guardrail to prevent premature imports.
- Added `docs/development/NEW_PLAN.md` (proposed self-validating CLI + manifest architecture); noted current blockers in the plan.

### CLI & Validation
- Added `setup-nvd` command; hardened `setup-secrets` token handling and cross-repo verification.
- Added template sync command/guard; validator fixes for summary drift and matrix key validation; wired Java POM checks into `cihub init`.
- Added CLI integration tests and correlation tests.

### Workflows & OWASP/NVD
- Fixed NVD/OWASP handling (use_nvd_api_key toggle, pass tokens) in central/reusable workflows; cleaned up workflow errors (duplicate keys, NameError).
- Note: the `setup-nvd`/NVD integration script still needs a follow-up fix; current version may not work end-to-end.

### Templates/Docs/Schema
- Updated caller templates and docs (TOOLS, WORKFLOWS, CONFIG_REFERENCE) alongside ADR updates; minor schema/report tweaks to match governance changes.

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

## 2025-12-19 - Job Summary Improvements & Multi-Module Support

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
- **Result parsing** - Parse emoji output (🎉 = killed, 🙁 = survived) instead of `mutmut results`
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
- Replaced `hub-run-all.yml` matrix builder with `scripts/load_config.py` to honor `run_group`, dispatch toggles, and all tool flags/thresholds from schema-validated configs
- Added `scripts/verify_hub_matrix_keys.py` to fail fast when workflows reference matrix keys that the builder does not emit
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

## 2025-12-15 (Evening)

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
- Updated workflow summaries to show all 12 tools with status indicators (✅ Ran / ⏭️ Skipped)
- Temporarily disabled contact-suite-spring config (900 tests, too slow for testing)

### Cross-Repo Authentication
- Added HUB_DISPATCH_TOKEN support for downloading artifacts from dispatched workflow runs
- Required for orchestrator to aggregate reports across repositories

---

## 2025-12-15

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
- Added requirements/ with P0, P1, and nonfunctional checklists.
- Replaced plan.md with a concise execution checklist linking to requirements.
- Added doc stubs extracted from the old plan: WORKFLOWS, CONFIG_REFERENCE, TOOLS, TEMPLATES, MODES, TROUBLESHOOTING, ADR index.
- Updated AGENTS to reflect current focus on P0 execution.
- Linked ROADMAP to requirements and noted planned phases.
- Hardened `hub-orchestrator.yml`: pass computed inputs, honor `default_branch`, set dispatch permissions, attempt run-id capture, emit dispatch metadata artifacts, and generate a hub summary/report from dispatch results.
- Added schema validation in orchestrator config load (jsonschema) to fail fast on bad repo configs; compiled scripts to ensure Python syntax.
- Captured dispatch metadata as artifacts for downstream aggregation; summaries now include per-repo dispatch info.
- Implemented aggregation pass to poll dispatched runs, fail on missing/failed runs, download `ci-report` artifacts when present, and roll up coverage/mutation into `hub-report.json`.
- Added schema validation to `scripts/load_config.py`; added `jsonschema` dependency to `pyproject.toml`.
- Added copy/paste templates: `templates/repo/.ci-hub.yml` and `templates/hub/config/repos/repo-template.yaml`.
- Added `config-validate` workflow to run schema validation on config/schema changes and PRs.
- Added ADR-0001 (Central vs Distributed) and expanded docs (CONFIG_REFERENCE, TOOLS, MODES, TROUBLESHOOTING, TEMPLATES).
- Fixed orchestrator config validation indentation bug and added dispatch run-id polling backoff/timeout.
- Added ADRs 0002-0005 (config precedence, reusable vs dispatch, aggregation, dashboard).
- Rewrote ADRs 0003-0006 to match actual implementation: ADR-0003 now accurately documents github-script dispatch mechanism; ADR-0004 now shows actual hub-report.json schema (runs[] array, not object); ADR-0005 added for Dashboard Approach (GitHub Pages); ADR-0006 added for Quality Gates and Thresholds.
