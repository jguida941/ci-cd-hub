# CLI/Wizard/Schema Sync Audit

**Status:** archived  
**Owner:** Development Team  
**Source-of-truth:** manual  
**Last-reviewed:** 2026-01-19  
**Superseded-by:** docs/development/active/TYPESCRIPT_CLI_DESIGN.md  
**Priority:** **#5** (Complete)  

## Superseded

This audit is complete and superseded by TypeScript CLI Phase 6 work in `docs/development/active/TYPESCRIPT_CLI_DESIGN.md`.

## Scope

Focus: wizard/CLI/schema alignment for repo setup and interactive flows, plus TypeScript CLI integration.

**Status update (2026-01-19):** Phase 5 cleanup complete; pending archive decision.

Reviewed sources:
- ADRs: `docs/adr/0025-cli-modular-restructure.md`, `docs/adr/0051-wizard-profile-first-design.md`, `docs/adr/0055-cli-dispatch-watch.md`
- Python CLI: `cihub/commands/*`, `cihub/cli_parsers/*`, `cihub/wizard/*`, `cihub/services/detection.py`
- Schema/defaults: `cihub/data/schema/ci-hub-config.schema.json`, `cihub/data/config/defaults.yaml`
- TypeScript CLI: `cihub-cli/src/*`

## Audit Methodology

Extended audit used cross-cutting reviews across workflows, exit codes, env vars, profiles, detection, templates, tests, and ADRs to surface boundary drift (8-agent deep dive).

## Findings (ordered by severity)

- [CRITICAL] Wizard advanced settings emit keys that are not in the schema, so wizard-generated configs can fail `cihub validate` and drift from defaults; mismatches include `gates.required/optional` vs `gates.require_run_or_fail/tool_defaults`, `reports.enabled/format` vs `reports.badges/codecov/github_summary/retention_days`, `notifications.slack.channel/on_failure_only` vs `notifications.slack.enabled/on_failure/on_success/webhook_env`, and `harden_runner.egress_policy` vs `harden_runner.policy` (`cihub/wizard/questions/advanced.py:12`, `cihub/wizard/questions/advanced.py:85`, `cihub/wizard/questions/advanced.py:135`, `cihub/wizard/questions/advanced.py:192`, `cihub/data/schema/ci-hub-config.schema.json:640`, `cihub/data/schema/ci-hub-config.schema.json:901`, `cihub/data/schema/ci-hub-config.schema.json:1000`, `cihub/data/schema/ci-hub-config.schema.json:1184`, `cihub/data/config/defaults.yaml:22`, `cihub/data/config/defaults.yaml:134`).
- [HIGH] TypeScript CLI forces `--json` for all commands, but several interactive commands explicitly reject JSON, so the interactive CLI cannot run `/setup`, `/config`, or `/config edit` (and any `--wizard` path) despite listing them in the registry (`cihub-cli/src/lib/cihub.ts:31`, `cihub-cli/src/app.tsx:183`, `cihub/commands/setup.py:98`, `cihub/commands/config_cmd.py:128`, `cihub/cli_parsers/config.py:38`).
- [HIGH] There is no CLI surface to pass a full config payload into `cihub init`, so a TypeScript wizard cannot hand off its selections to Python CLI without re-implementing config building (violates “wizard is a UX layer over handlers”) (`cihub/commands/init.py:149`, `cihub/cli_parsers/repo_setup.py:52`).
- [HIGH] Schema defaults for `install` and `harden_runner` are missing from `defaults.yaml`, so wizard base configs and effective configs omit schema-defaulted keys; this breaks the “schema → defaults → wizard” contract (`cihub/data/schema/ci-hub-config.schema.json:1160`, `cihub/data/schema/ci-hub-config.schema.json:1184`, `cihub/data/config/defaults.yaml:210`).
- [HIGH] Per-tool `require_run_or_fail` defaults exist in the schema but are missing across tool defaults, so effective configs do not reflect schema-defaulted gate behavior (`cihub/data/schema/ci-hub-config.schema.json:234`, `cihub/data/schema/ci-hub-config.schema.json:401`, `cihub/data/config/defaults.yaml:74`, `cihub/data/config/defaults.yaml:149`).
- [HIGH] Packaging defaults are misaligned: schema defaults `install.source` to `pypi`, but `cihub init` defaults to `git` and the repo template builder defaults to `pypi`, violating the “defaults aligned across schema/CLI/docs” contract (`cihub/data/schema/ci-hub-config.schema.json:1171`, `cihub/cli_parsers/repo_setup.py:91`, `cihub/commands/init.py:115`, `cihub/services/templates.py:34`).
- [MEDIUM] Command registry metadata is misleading for wizard support: it only flags `--wizard`, while `new` uses `--interactive` and `config edit` is wizard-only without a flag; consumers cannot reliably infer which commands are interactive (`cihub/commands/commands_cmd.py:103`, `cihub/cli_parsers/repo_setup.py:36`, `cihub/cli_parsers/config.py:56`, `cihub/commands/config_cmd.py:128`).
- [MEDIUM] Command registry `supports_json` is derived from argparse flags even when runtime blocks JSON (e.g., `setup`, `config edit`), so the registry overstates JSON support (`cihub/commands/commands_cmd.py:107`, `cihub/commands/setup.py:98`, `cihub/commands/config_cmd.py:128`).
- [MEDIUM] `report security-summary`, `report smoke-summary`, `report kyverno-summary`, and `report orchestrator-summary` lack `--json` flags, so JSON enforcement in the TypeScript CLI and registry support are out of sync (`cihub/cli_parsers/report.py:197`, `cihub/cli_parsers/report.py:227`, `cihub/cli_parsers/report.py:262`, `cihub/cli_parsers/report.py:282`).
- [MEDIUM] TypeScript CLI does not validate `supports_json` or `is_group` before execution; parent group commands (e.g., `/docs`, `/commands`) error and then fail JSON parsing (`cihub-cli/src/lib/cihub.ts:31`, `cihub-cli/src/commands/index.ts:124`, `cihub-cli/src/app.tsx:183`).
- [MEDIUM] `cihub new --interactive` builds from defaults (wizard) while non-interactive `cihub new` builds from the repo template; the two paths produce different config shapes (e.g., unused language block pruning and `install` block presence), which breaks “interactive = non-interactive” parity (`cihub/commands/new.py:80`, `cihub/wizard/core.py:145`, `cihub/services/templates.py:27`).
- [MEDIUM] The onboarding wizard cannot configure several schema fields (e.g., `repo.default_branch`, `repo.dispatch_enabled`, `repo.dispatch_workflow`, `repo.force_all_tools`, `repo.run_group`, `repo.subdir`, `install.source`, `notifications.email`, `notifications.slack.webhook_env`), so interactive setup cannot reach full schema coverage without dropping to `config set` or manual edits (`cihub/wizard/core.py:84`, `cihub/wizard/questions/advanced.py:135`, `cihub/data/schema/ci-hub-config.schema.json:1000`, `cihub/data/schema/ci-hub-config.schema.json:1089`, `cihub/data/schema/ci-hub-config.schema.json:1160`).
- [MEDIUM] Wizard does not expose several top-level feature toggles (`cache_sentinel`, `canary`, `chaos`, `dr_drill`, `egress_control`, `runner_isolation`, `supply_chain`, `telemetry`, `kyverno`, `cihub`), so those schema sections are unreachable via interactive setup (`cihub/wizard/core.py:145`, `cihub/data/schema/ci-hub-config.schema.json:800`, `cihub/data/schema/ci-hub-config.schema.json:1160`).
- [MEDIUM] Python docker defaults omit `dockerfile` even though the schema defines it (defaults diverge from schema defaults) (`cihub/data/schema/ci-hub-config.schema.json:447`, `cihub/data/config/defaults.yaml:166`).
- [MEDIUM] Wizard prompts for `semgrep`/`trivy`/`codeql` twice (once in tool selection, again in security prompts), creating redundant and potentially conflicting answers (`cihub/wizard/core.py:154`, `cihub/wizard/questions/security.py:11`, `cihub/tools/registry.py:40`).
- [MEDIUM] Tier selection is captured by the wizard, but repo-side `init --wizard` ignores the tier output, so users select a tier that does not influence generated config unless they are using the hub registry path (`cihub/wizard/core.py:22`, `cihub/commands/init.py:139`, `cihub/commands/new.py:95`).
- [MEDIUM] Wizard thresholds only expose `coverage_min` and `mutation_score_min`, leaving many schema thresholds unreachable via wizard (e.g., vuln caps, lint caps), which blocks “wizard can do everything” for repo setup (`cihub/wizard/questions/thresholds.py:15`, `cihub/data/schema/ci-hub-config.schema.json:709`).
- [MEDIUM] `cihub scaffold --wizard` does not block `--json`, so a JSON-mode run can still enter interactive prompts and corrupt JSON output (`cihub/commands/scaffold.py:198`).
- [LOW] Schema uses different types for `trivy.fail_on_cvss` between Java (integer) and Python (number), which is an internal schema inconsistency (`cihub/data/schema/ci-hub-config.schema.json:390`, `cihub/data/schema/ci-hub-config.schema.json:629`).

## Deferred (out of scope for current plan)

- Schema allows `node`/`go`, but wizard language selection, detection, and CLI `--language` choices are Java/Python only (`cihub/wizard/questions/language.py:12`, `cihub/services/detection.py:8`, `cihub/cli_parsers/repo_setup.py:21`, `cihub/data/schema/ci-hub-config.schema.json:990`).

## Decisions (2026-01-18)

- Canonical install default is **PyPI**; align CLI defaults and templates to the schema default.
- v1.0 supports **Java/Python only**; constrain schema language enum accordingly and defer Node/Go until strategies exist.
- Command registry should include explicit `supports_interactive` and `supports_json_runtime` signals (no reliance on argparse-only flags).

## Open Questions / Assumptions

- Should the TypeScript wizard drive Python CLI via a new JSON input surface (e.g., `--config-json`/`--config-file`) to avoid parallel config logic?
- Should interactive-only commands be hidden from the TypeScript CLI until a non-JSON pathway exists?
- Should wizard onboarding cover the full repo/notifications/install surface, or should advanced fields remain CLI-only?

## Suggested Next Actions (non-blocking)

- Align wizard advanced prompts with schema (or deprecate those prompts until schema contracts are updated).
- Add missing schema defaults (`install`, `harden_runner`) to `defaults.yaml` generation so wizard base configs match schema defaults.
- Add a headless config input for `cihub init`/`cihub new` to support the TypeScript wizard.
- Extend `commands list` to express JSON support accurately (including “not with --wizard” constraints), and add an `supports_interactive` signal for `--interactive`/wizard-only commands.
- Guard `cihub scaffold --wizard` from `--json` to preserve JSON purity.

---

## Extended Audit Findings (2026-01-18)

The following findings were discovered by a comprehensive 8-agent deep-dive audit covering workflow alignment, exit codes, environment variables, profiles, detection, templates, test coverage, and ADR implementation.

### Workflow YAML Alignment

- [MEDIUM] `NVD_API_KEY` secret is declared in `java-ci.yml:222-223` and `use_nvd_api_key` input is accepted, but the secret is never passed to `cihub ci` at line 314-332. OWASP/NVD scanning cannot use the API key.
- [MEDIUM] Bootstrap script installation (`curl | python`) in `python-ci.yml:268-269` is inconsistent with `pip install -e` method used elsewhere. If bootstrap fails, there is no fallback.
- [LOW] Boolean string format inconsistency: workflows use `'True'`/`'False'` (Python style) but `env_registry.py` documents defaults as `"true"`/`"false"` (JSON style).

### Exit Code Consistency

- [HIGH] Magic numbers in `cihub/commands/commands_cmd.py`: line 161 uses `exit_code=0` and line 171 uses `exit_code=2` instead of `EXIT_SUCCESS`/`EXIT_USAGE` constants.
- [MEDIUM] Comparisons to `== 0` instead of `== EXIT_SUCCESS` in `cihub/output/renderers.py:248`, `cihub/commands/check.py:269`, `cihub/commands/smoke.py:395,419`.
- [LOW] `EXIT_DECLINED`, `EXIT_INTERNAL_ERROR`, and `EXIT_INTERRUPTED` exit codes are defined but have zero test coverage.

### Environment Variable Registry

- [HIGH] Env vars used in code but not registered in `env_registry.py`: `GITHUB_*` context variables (e.g., `GITHUB_OUTPUT`, `GITHUB_STEP_SUMMARY`, `GITHUB_RUN_ID`), `GH_*` aliases (`GH_REPOSITORY`, `GH_REF_NAME`, `GH_RUN_NUMBER`, `GH_EVENT_NAME`), and tool/CI vars (`TOTAL_REPOS`, `HUB_RUN_ID`, `HUB_EVENT`, `GITLEAKS_OUTCOME`, `QUARANTINE_EXCLUDE_DIRS`, `KYVERNO_BIN`, `VIRTUAL_ENV`) (`cihub/utils/github_context.py:98`, `cihub/commands/report/aggregate.py:93`, `cihub/commands/hub_ci/release.py:842`, `cihub/commands/hub_ci/validation.py:477`, `cihub/commands/hub_ci/release.py:969`, `cihub/core/ci_runner/shared.py:31`, `cihub/utils/env_registry.py:90`).
- [MEDIUM] Non-standard `GH_REPOSITORY`, `GH_REF_NAME`, `GH_RUN_NUMBER`, `GH_EVENT_NAME` aliases in `cihub/commands/hub_ci/release.py:969-972` instead of standard `GITHUB_*` names.
- [MEDIUM] Multiple files directly call `os.environ.get("GITHUB_*")` instead of using centralized `GitHubContext.from_env()` (15+ files scattered).

### Profile Configuration

- [MEDIUM] **23 of 24 profiles** are missing `_metadata` section (only `python-fast.yaml` has it). Wizard falls back to `_FALLBACK_PROFILE_INFO` with generic descriptions (`cihub/wizard/questions/profile.py:18-49`).
- [LOW] `python-fast.yaml` metadata claims `tools: pytest, ruff, black, bandit, pip-audit` but actual enabled tools include `isort` which is missing from the description.

### Detection Service Alignment

- [HIGH] Schema allows 4 languages (`java`, `python`, `node`, `go`) but detection service only implements 2. CLI parsers hardcode `choices=["java", "python"]` (`cihub/cli_parsers/repo_setup.py:23,57,105`).
- [HIGH] Only `JavaStrategy` and `PythonStrategy` classes exist in `cihub/core/languages/registry.py:19-30`. Attempting `cihub ci` with `language: node` or `language: go` raises `ValueError: Unsupported language`.
- [MEDIUM] Two different detection implementations exist: `cihub/services/detection.py` (simple file checks, no confidence) vs `cihub/core/languages/registry.py` (confidence-based scoring). Legacy version cannot disambiguate mixed Java/Python repos.

### Template Generation

- [MEDIUM] All 14 profiles in `cihub/data/templates/profiles/` fail standalone schema validation because they are partial configs for merging. This is by design but not documented in the schema.
- [LOW] User-facing templates (`.ci-hub.yml`, `repo-template.yaml`, `monorepo-template.yaml`) contain schema-valid placeholder values that must be edited before use; add explicit "EDIT BEFORE USE" markers.

### Test Contract Coverage

- [MEDIUM] `test_command_result_has_expected_fields` at line 226 is a placeholder (`pass`), so per-command CommandResult field expectations are documented but not enforced (`tests/contracts/test_command_output_contract.py:218`).

### ADR Implementation

- [OK] All 8 ADRs reviewed (0025, 0031, 0042, 0051, 0054, 0055, 0056, 0057, 0058) show strong alignment between decisions and implementation. No contradictions found.
- [LOW] ADR-0051 and ADR-0055 are marked "Implemented" but should probably be "Accepted" since they represent ongoing features.

---

## Summary Statistics

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Wizard/Schema (original) | 1 | 4 | 11 | 1 | 17 |
| Packaging Defaults | 0 | 1 | 0 | 0 | 1 |
| Workflow Alignment | 0 | 0 | 2 | 1 | 3 |
| Exit Codes | 0 | 1 | 1 | 1 | 3 |
| Environment Variables | 0 | 1 | 2 | 0 | 3 |
| Profile Configuration | 0 | 0 | 1 | 1 | 2 |
| Detection Service | 0 | 2 | 1 | 0 | 3 |
| Template Generation | 0 | 0 | 1 | 1 | 2 |
| Test Coverage | 0 | 0 | 1 | 0 | 1 |
| ADR Implementation | 0 | 0 | 0 | 1 | 1 |
| **Total** | **1** | **9** | **20** | **6** | **36** |

## Top User-Facing Breakages (Verified)

- Wizard emits non-schema keys, so wizard-generated configs can fail `cihub validate` (`cihub/wizard/questions/advanced.py:12`, `cihub/data/schema/ci-hub-config.schema.json:640`).
- TypeScript CLI appends `--json` unconditionally, so interactive commands (`/setup`, `/config edit`) fail despite being listed in the registry (`cihub-cli/src/lib/cihub.ts:31`, `cihub/commands/setup.py:98`).
- Schema allows `node`/`go`, but implementation only supports Java/Python; `cihub ci` can fail with `Unsupported language` (`cihub/data/schema/ci-hub-config.schema.json:990`, `cihub/core/languages/registry.py:19`).
- Per-tool `require_run_or_fail` defaults are missing in `defaults.yaml`, so gate behavior diverges from schema defaults (`cihub/data/schema/ci-hub-config.schema.json:234`, `cihub/data/config/defaults.yaml:74`).

## Root Cause Pattern

- Schema is more permissive than implementation (languages, thresholds, notifications), so configs can validate but fail at runtime; align schema or implementation to close the gap (`cihub/data/schema/ci-hub-config.schema.json:990`, `cihub/core/languages/registry.py:19`).

## What's Working Well (Verified)

- Wizard tool selection sources tool lists from the registry (including custom tools), matching CLI tool registry usage (`cihub/wizard/questions/python_tools.py:10`, `cihub/wizard/questions/java_tools.py:10`, `cihub/commands/tool_cmd.py:12`).
- CommandResult schema is compatible between Python and TypeScript (TS uses `.passthrough()`), so extra fields do not break the TS CLI (`cihub/types.py:14`, `cihub-cli/src/types/command-result.ts:1`).
- Interactive `setup` and `config edit` correctly reject `--json`, preserving JSON purity on those commands (`cihub/commands/setup.py:98`, `cihub/commands/config_cmd.py:128`).
- Command output contract test enforces no `print()` calls in `cihub/commands` (`tests/contracts/test_command_output_contract.py:76`).
- `build_repo_config()` fills required repo fields using the `.ci-hub.yml` template (`cihub/services/templates.py:27`, `cihub/data/templates/repo/.ci-hub.yml:1`).

---

## Prioritized Remediation Plan

### Phase 1: Critical Fixes (Block releases)

1. [x] Fix wizard `advanced.py` to emit schema-valid keys (CRITICAL)
2. [x] Add `require_run_or_fail` to all 26 tools in `defaults.yaml` (HIGH)
3. [x] Add missing schema defaults (`install`, `harden_runner`) to `defaults.yaml` (HIGH)
4. [x] Align `install` defaults to PyPI across CLI + templates (HIGH)

### Phase 2: TypeScript Integration (User-facing)

5. [x] Check `supports_json` in `cihub-cli/src/lib/cihub.ts` before appending `--json` (HIGH)
6. [x] Add `supports_interactive` + `supports_json_runtime` to `commands list` payload (HIGH)
7. [x] Add `--json` flags to 4 report summary commands in `report.py` (MEDIUM)
8. [x] Handle parent groups (`is_group`) specially in TS CLI (MEDIUM)

### Phase 3: Detection & Language (Consistency)

9. [x] Constrain schema to `["java", "python"]` for v1.0 (defer Node/Go) (HIGH)
10. [x] Consolidate detection implementations to single confidence-based approach (MEDIUM)

### Phase 4: Test Coverage (Quality)

11. [x] Replace placeholder `test_command_result_has_expected_fields` with enforced checks (MEDIUM)

### Phase 5: Documentation & Cleanup

12. [x] Add `_metadata` to remaining profiles (MEDIUM)
13. [x] Centralize GitHub context reading via `GitHubContext.from_env()` (MEDIUM)
14. [x] Replace magic exit code numbers with constants (LOW)
