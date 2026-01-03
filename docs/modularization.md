# CIHUB Modularization Plan (Behavior Preserving)

Status: Draft

## Intent

- Modularize all code under `cihub/` to improve organization, testability, and PyQt6 GUI integration.
- Preserve all runtime behavior, CLI surface, defaults, and output formats.

## Non-Goals

- No logic changes, no new features, no data format changes.
- No CLI flag changes, defaults changes, or help-order changes.
- No schema or config changes.
- No new runtime dependencies (dev-only tools are optional).

## Definition of "Modularized"

- Split large modules into smaller modules or packages.
- Move shared helpers into `cihub/utils/`.
- Keep original import paths stable via facades and explicit re-exports.
- Preserve lazy imports and CLI `--help` output ordering.

## Public API and GUI Alignment

- GUI should depend on `cihub.services.*`, not `cihub.cli`.
- CLI remains the entrypoint (`cihub.cli` and `python -m cihub`).
- Commands remain CLI adapters; services remain programmatic API.
- Services should not import `cihub.cli`; shared helpers live in `cihub/utils`.

## Layering Rules (No Behavior Change, Only Boundaries)

- utils/types: stdlib only
- config: utils/types
- core: utils/types/config
- services: utils/types/config/core
- commands: services + core + utils
- cli: commands + services + utils

## Target Package Map (Post-Modularization)

```
cihub/
  __init__.py
  __main__.py
  cli.py                      # entrypoint + facade re-exports
  cli_parsers/                # parser-only modules (no handler imports)
    __init__.py
    base.py
    report.py
    hub_ci.py
    ...
  types.py                    # CommandResult
  utils/
    __init__.py
    env.py                    # _parse_env_bool
    progress.py               # _bar
    paths.py                  # hub_root, validate_repo_path, validate_subdir
    git.py                    # get_git_branch, get_git_remote, parse_repo_from_remote
    exec_utils.py             # resolve_executable, run helpers
    github_api.py             # gh_api_json, fetch_remote_file
    java_pom.py               # POM helpers
  core/
    __init__.py
    aggregation.py
    ci_runner.py
    ci_report.py
    reporting.py
    badges.py
    correlation.py
  tools/
    __init__.py
    registry.py               # tool definitions (behavior-preserving)
  services/
    __init__.py
    ci_engine/                # package facade for ci_engine
      __init__.py
      python_tools.py
      java_tools.py
      gates.py
      io.py
      notifications.py
      helpers.py
    discovery.py
    report_validator.py
    aggregation.py
    configuration.py
    report_summary.py
    types.py
  commands/
    __init__.py
    hub_ci/                   # package facade for hub_ci
      __init__.py
      python_tools.py
      java_tools.py
      security.py
      validation.py
      badges.py
      smoke.py
      release.py
    report/                   # package facade for report
      __init__.py
      build.py
      aggregate.py
      outputs.py
      summary.py
      validate.py
      dashboard.py
      helpers.py
    adr.py
    check.py
    ci.py
    config_cmd.py
    config_outputs.py
    detect.py
    discover.py
    dispatch.py
    docs.py
    init.py
    new.py
    pom.py
    preflight.py
    run.py
    scaffold.py
    secrets.py
    smoke.py
    templates.py
    update.py
    validate.py
    verify.py
  config/
    __init__.py
    loader/                   # package facade for loader
      __init__.py
      inputs.py
      profiles.py
      defaults.py
    io.py
    merge.py
    normalize.py
    paths.py
    schema.py
  wizard/
    __init__.py
    core.py
    prompts.py                # optional helper extraction
    questions/
    validators.py
    summary.py
    styles.py
  diagnostics/
    __init__.py
    models.py
    renderer.py
    collectors/
      __init__.py
```

Notes:
- `cihub.cli` stays a module (not a package) for compatibility.
- `hub_ci` and `report` become packages; facades live in their `__init__.py`.
- `ci_engine` and `config.loader` become packages; facades live in `__init__.py`.

## Compatibility Strategy

- Each moved module has a facade at the original import path.
- Use explicit `__all__` to preserve private helper imports used in tests.
- `cihub.cli` re-exports moved helpers and `CommandResult`.
- `mock.patch` targets must remain valid (update strings or keep wrapper functions).

## Phase Plan (Behavior Preserving)

### Phase 0: Baseline and Safety Rails

Required before any code moves.

- Snapshot CLI help output for regression detection.
- Add `tests/test_module_structure.py`:
  - mock.patch target resolution across `tests/` and `mutants/tests/`.
  - import smoke for `cihub`, `cihub.cli`, `cihub.commands.hub_ci`, `cihub.commands.report`, `cihub.services.ci_engine`.
  - locked hub_ci command count (47).
- Add aggregate-report partial-data regression test (aggregate must render even if some repos fail).
- Inventory current imports of `cihub.cli` to define the public facade list.
- Document layering rules in this plan (done above).

### Phase 1: Utilities Extraction (Low Risk)

- Create `cihub/utils/env.py` with `_parse_env_bool` (no signature change).
- Create `cihub/utils/progress.py` with `_bar` (no signature change).
- Extract CLI helpers into `cihub/utils/`:
  - paths: `hub_root`, `validate_repo_path`, `validate_subdir`.
  - git: `get_git_branch`, `get_git_remote`, `parse_repo_from_remote`.
  - exec: `resolve_executable`, shared subprocess helpers.
  - github: `gh_api_json`, `fetch_remote_file`.
  - java_pom: POM helper functions.
- Extract `CommandResult` to `cihub/types.py` and re-export from `cihub.cli`.
- Update imports to use `cihub/utils/*` or `cihub/types`.
- Keep `cihub.cli` re-exports for all moved items.

### Phase 2: Tool Registry Modularization (Medium Risk)

- Create `cihub/tools/registry.py` with the exact tool lists and metric maps currently in:
  - `cihub/services/ci_engine.py`
  - `cihub/services/discovery.py`
  - `cihub/services/report_validator.py`
- Preserve ordering and content exactly (no tool additions/removals).
- Update imports to use `cihub.tools.registry`.
- Add tests that enforce strict equality and ordering (no drift).
- Keep ADR-0035 registry separate (this is an internal tool registry only).

### Phase 3: Commands Modularization (High Risk)

#### Phase 3a: Split `commands/hub_ci.py` (Strangler Approach)

- Extract groups into `cihub/commands/hub_ci/*.py` while keeping behavior identical.
- Keep helpers with their command group unless shared across groups.
- Preserve lazy imports inside command bodies (do not lift them).
- After extraction, convert `hub_ci.py` to package `hub_ci/` in a single commit.
- Ensure `cihub.commands.hub_ci` still exposes all 47 `cmd_*` functions and private helpers.

#### Phase 3b: Split `commands/report.py`

- Extract subcommands into `cihub/commands/report/*.py`:
  - build, aggregate, outputs, summary, validate, dashboard, helpers
- Keep `cmd_report` as the router in `cihub/commands/report/__init__.py`.
- Preserve signature differences (do not unify `_append_summary`).
- Convert `report.py` to package `report/` in a single commit.

### Phase 4: Services Modularization (High Risk)

- Convert `cihub/services/ci_engine.py` to package `ci_engine/` with facade `__init__.py`.
- Move python/java tool logic, gate evaluation, and IO helpers into submodules.
- Keep the original function names and signatures available via `cihub.services.ci_engine`.
- Remove services -> cli imports by routing through `cihub/utils` (behavior unchanged).

### Phase 5: Core Module Organization (Low Risk)

- Move root modules to `cihub/core/`:
  - `aggregation.py`, `ci_runner.py`, `ci_report.py`, `reporting.py`, `badges.py`, `correlation.py`
- Keep facade modules at original paths with explicit `__all__`.

### Phase 6: CLI Parser Modularization (Medium Risk)

- Extract parser setup into `cihub/cli_parsers/*` modules (parser-only, no handler imports).
- Keep stub handler functions in `cihub/cli.py` (lazy imports preserved).
- Use explicit registry ordering in `cli.py` to preserve `--help` output ordering.

### Phase 7: Config Loader Modularization (Medium Risk)

- Convert `cihub/config/loader.py` to package `config/loader/`.
- Split `generate_workflow_inputs()` and related helpers into submodules.
- Keep `cihub.config.loader` import path stable via facade `__init__.py`.

### Phase 8: Wizard and Diagnostics Tidying (Low Risk)

- Optional: extract repeated prompt patterns into `cihub/wizard/prompts.py`.
- Preserve all prompts, defaults, and output formatting.

## Testing and Go/No-Go Gates (All Phases)

- `pytest tests/` (plus `mutants/tests` if applicable)
- CLI help snapshot unchanged
- mock.patch target resolution test
- aggregate-report partial-data test
- command count lock for hub_ci
- no new circular imports (optional `pydeps --show-cycles` as a dev-only tool)

## Rollback Strategy

- One commit per phase.
- If a phase fails tests, revert that single commit and fix in isolation.

## Notes

- This plan is strictly behavior-preserving. Any refactor that changes logic is out of scope.
- If this plan is approved for execution, update `docs/development/PLAN.md` checkboxes to reflect active scope.
