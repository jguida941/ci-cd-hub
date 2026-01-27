# CIHub Architecture Audit

**Status:** active
**Owner:** Development Team
**Source-of-truth:** manual
**Last-reviewed:** 2026-01-26

## Purpose

Audit CIHub architecture against the documented contract and current runtime
behavior, then define a fix plan for the gaps found during tool audits.

## Scope

- Python CLI command surface and tool runners.
- Report schema, tool evidence, and validator semantics.
- Triage outputs and verification logic.
- Workflow wrappers and artifact layout.
- TypeScript CLI passthrough and wizard handoff.

## Inputs

- `docs/development/MASTER_PLAN.md`
- `docs/development/architecture/ARCH_OVERVIEW.md`
- `docs/development/architecture/DESIGN_JOURNEY.md`
- `docs/development/active/TYPESCRIPT_CLI_DESIGN.md`
- `TOOL_TEST_AUDIT_PLAN.md`
- `docs/development/research/CIHUB_TOOL_RUN_AUDIT.md`

## Architecture Contract (summary)

- CLI is the product and headless API; command names are stable endpoints.
- Schema is the config contract and single source of truth for defaults.
- Workflows are thin wrappers that only call `cihub` commands.
- Tool execution must emit evidence; success must match gates and reports.
- All commands should support `--json` and return `CommandResult`.

## Findings (ordered by severity)

1. Tool success semantics diverge from gate semantics.
   - Evidence: bandit tool-outputs reported `success=false` while report
     `tools_success.bandit=true` for low findings.
   - Impact: report validator errors and false failures in triage.
   - Fix: align tool-output success with gate-derived `tools_success` for
     tools whose exit codes represent findings (bandit, pip_audit, mutmut).
   - Note: report validator should not fail when `success=true` and tool
     returncodes are non-zero due to findings (warn instead).

2. Tool artifact paths are recorded as absolute runner paths.
   - Evidence: report validator warns about missing artifacts after download
     because paths point to `/home/runner/...`.
   - Impact: evidence verification warns even when artifacts exist in the
     downloaded `.cihub/` directory.
   - Fix: normalize tool artifact paths to be relative to `.cihub/` or
     output_dir so artifacts remain resolvable after download.

3. Fixture repos can fail security gates due to real vulnerabilities.
   - Evidence: `pip_audit` failed in a passing fixture repo.
   - Impact: fixture "passing" repos do not pass without repo-specific
     threshold overrides.
   - Fix: configure fixture repos to allow known vuln counts or pin deps
     (requires approval to change repo config files).

4. `init`/`setup` rely on gh auth for hub var verification.
   - Evidence: `cihub init --apply` failed when gh was not authenticated.
   - Impact: audit flow must use `--no-set-hub-vars` or ensure gh auth.
   - Fix: document the requirement in audit steps and keep failure as
     designed (ADR-0072).

5. Real repo audits can complete without downloadable artifacts.
   - Evidence: `java-spring-tutorials` run 21353926655 and `cs-320-portfolio`
     run 21356266495 produced no artifacts; `contact-suite-spring-react`
     run 21356273903 also lacked report artifacts.
     triage fell back to log parsing and `--verify-tools` could not run.
   - Impact: tool evidence cannot be verified, blocking the audit contract.
   - Root cause (most likely): caller workflows pass empty `hub_repo`/`hub_ref`
     when `HUB_REPO/HUB_REF` vars are unset, so the hub workflow cannot
     install `cihub` and never writes `.cihub/report.json`.
   - Fix: default `hub_repo`/`hub_ref` in hub workflows and caller templates,
     and ensure `cihub ci` always writes a minimal failure report when config
     or tool execution fails (so artifacts exist even on failures).

6. `cihub dispatch trigger` fails (404) when workflow exists only on an audit branch.
   - Evidence: `cs320-orig-contact-service`, `contact-suite-spring-react`,
     `dijkstra-dashboard` audit branches return 404 for `hub-ci.yml`.
   - Impact: CLI cannot dispatch audit-branch workflows on repos that lack
     the workflow file on the default branch; audits stall despite push runs.
   - Fix: CLI should detect 404 and fall back to watching latest runs on the
     audit branch (push-triggered), or surface a clear remediation path.

## Fix Plan (phased)

### Phase A: Tool success alignment

- Align `success` in tool-outputs with gate semantics.
- Targets: bandit (respect `max_high_vulns`), pip_audit, mutmut, Python
  lint/security tools (ruff/black/isort/semgrep/trivy), Java
  lint/security/coverage tools (jacoco/pitest/checkstyle/spotbugs/pmd/owasp/trivy).
- Tests: unit tests in `tests/unit/services/ci_engine/` and report validation.
- Status: implemented (tool-outputs success now gate-derived across Python/Java;
  validator warns on non-zero returncodes when success is gate-based).
- Follow-up: add regression tests for ruff/black/isort/semgrep/trivy/jacoco/pitest/checkstyle/spotbugs/pmd/owasp.
- Additional fix: OWASP Maven runner uses `aggregate` for multi-module projects
  to improve report generation reliability.

### Phase B: Artifact path normalization

- Store artifact paths relative to `.cihub/` or output_dir.
- Update report validator to resolve relative paths against report dir.
- Add tests for artifact resolution in `tests/unit/services/report_validator/`.
- ADR required if this changes report contract expectations.

### Phase C: Fixture repo gating

- Decide on fixture policy: allow vulnerabilities or pin dependencies.
- Apply overrides in `cihub/data/config/repos/` (requires approval).
- Add regression tests for fixture thresholds.
 - Interim: `cihub-test-python-pyproject`, `cihub-test-python-src-layout`, and `cihub-test-python-setup` use `max_pip_audit_vulns: 1` in repo `.ci-hub.yml` (now on main) to pass `pip_audit` until a fix is available.

### Phase D: Re-run audit matrix

- Re-run repo matrix with `cihub dispatch` + `cihub triage --verify-tools`.
- Log all runs in `docs/development/research/CIHUB_TOOL_RUN_AUDIT.md`.

### Phase E: Real repo artifact verification

- Re-triage `java-spring-tutorials` after enforcing hub repo/ref defaults and
  failure report emission.
- Add a regression check that `report.json` exists for real repo runs, even
  when `cihub ci` fails early.

### Phase F: Dispatch fallback for audit branches

- Detect 404 from GitHub workflow dispatch and guide users to
  `cihub dispatch watch --latest --workflow hub-ci.yml --branch <audit>`.
- Optionally add an automatic fallback to "watch latest" when dispatch fails.

## Audit execution (architecture-aligned)

- Execution plan lives in `TOOL_TEST_AUDIT_PLAN.md`, including real repo
  inventory, ref strategy, and evidence rules.
- "Works" means tools run with evidence and triage/verify-tools has zero
  unknown or no-report statuses; failures reflect true repo issues.

## Open Decisions

- Should tool output artifacts be stored as relative paths or mapped during
  report validation?
- Should `pip_audit` treat exit code 1 as non-fatal when `fail_on_vuln=false`?
- Should fixtures allow vulnerabilities by default or pin dependencies?
- Workflow ref override is accepted via `repo.hub_workflow_ref` and
  `--hub-workflow-ref` for audit branches (ADR-0073).

## Verification

- `cihub triage --verify-tools` reports zero unknown/no-report.
- Report validator has zero mismatches for tools with findings.
- TS CLI passthrough mirrors Python CLI output for audited commands.
