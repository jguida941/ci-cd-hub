# CIHUB Modularization Plan (Behavior Preserving) - Updated With Guardrails

> **WARNING: SUPERSEDED:** This modularization plan was executed. See `docs/development/active/CLEAN_CODE.md` for ongoing architecture work and `docs/development/archive/Jan3.md` for execution history.
>
> **Status:** Archived (Completed)

This is your plan, kept behavior-preserving, but tightened so it does not sprawl and so you do not accidentally mix refactor work with new feature work (triage). I also added progressive boundary enforcement, a single canonical config loader rule, and a clear re-export policy so cli.py does not become a permanent dumping ground.

⸻

Intent
	•	Modularize all code under cihub/ to improve organization, testability, and PyQt6 GUI integration.
	•	Preserve all runtime behavior, CLI surface, defaults, and output formats.

Non-Goals
	•	No logic changes, no new features, no data format changes.
	•	No CLI flag changes, default changes, or help-order changes.
	•	No schema or config changes.
	•	No new runtime dependencies (dev-only tools are optional).

⸻

Split Into Two Tracks (Do Not Blend)

Track A: Modularization (this plan)
	•	Moving code into utils/, services/, core/, packages.
	•	Re-exports and facades keep import paths stable.
	•	No new output files, no new artifacts, no new CLI behavior.

Track B: Triage Outputs (separate plan)
	•	Failure bundle, artifacts layout, stable triage schema, LLM prompt pack.
	•	This WILL change outputs and files.
	•	Do not implement any triage behavior while doing Track A Phases 0-7.

Hard rule:
	•	While executing Track A phases, do not add any new outputs, files, or behavior. Only move code.

⸻

Definition of “Modularized”
	•	Split large modules into smaller modules or packages.
	•	Move shared helpers into cihub/utils/.
	•	Keep original import paths stable via facades and explicit re-exports.
	•	Preserve lazy imports and CLI --help output ordering.

⸻

Public API and GUI Alignment
	•	GUI should depend on cihub.services.*, not cihub.cli.
	•	CLI remains the entrypoint (cihub.cli and python -m cihub).
	•	Commands remain CLI adapters; services remain programmatic API.
	•	Services must not import cihub.cli; shared helpers live in cihub/utils.

End-state rule (important):
	•	New code must not import from cihub.cli.
	•	Only legacy callers may keep importing from cihub.cli until migrated.

⸻

Layering Rules (Boundaries Only)
	•	utils/types: stdlib only
	•	config: utils/types
	•	core: utils/types/config
	•	services: utils/types/config/core
	•	commands: services + core + utils
	•	cli: commands + services + utils

⸻

Canonical Config Loader Invariant (Non-Negotiable)

There must be exactly one canonical config loader that performs schema validation.

Rules:
	•	Every other “loader” function delegates to the canonical loader.
	•	No duplicate deep-merge logic scattered across CLI/services/commands.
	•	Do not change public signatures. Wrap and derive required inputs internally.

This is the exact failure you are preventing: “worked locally but broke in CI” because one loader validates and one does not.

⸻

Engines and Polymorphism (Only Where It Kills Branching)

Use polymorphism only if it removes duplicated if language == ... branching in 3+ places.

Clean target pattern:
	•	ToolRunner (core) runs a tool given a command spec
	•	LanguageEngine (services/core boundary) produces command spec and artifact expectations
	•	CLI selects engine and calls service

Do not force classes everywhere. Use them where they reduce branching and centralize rules.

⸻

Target Package Map (Post-Modularization)

cihub/
 __init__.py
 __main__.py
 cli.py # entrypoint + facade re-exports
 cli_parsers/ # parser-only modules (no handler imports)
 __init__.py
 base.py
 report.py
 hub_ci.py
 ...
 types.py # CommandResult
 utils/
 __init__.py
 env.py
 progress.py
 paths.py
 git.py
 exec_utils.py
 github_api.py
 java_pom.py
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
 registry.py
 services/
 __init__.py
 ci_engine/
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
 hub_ci/
 __init__.py
 python_tools.py
 java_tools.py
 security.py
 validation.py
 badges.py
 smoke.py
 release.py
 report/
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
 loader/
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
 prompts.py
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

Notes:
	•	cihub.cli stays a module (not a package) for compatibility.
	•	hub_ci and report become packages; facades live in their __init__.py.
	•	ci_engine and config.loader become packages; facades live in __init__.py.

⸻

Compatibility Strategy
	•	Each moved module has a facade at the original import path.
	•	Use explicit __all__ to preserve private helper imports used in tests.
	•	cihub.cli re-exports moved helpers and CommandResult.
	•	mock.patch targets must remain valid (either keep wrapper functions or preserve import paths).

Re-export discipline:
	•	If anything was imported from cihub.cli previously, keep it working for now.
	•	But stop new internal imports from cihub.cli as you touch files (migrate them to services/utils).

⸻

Phase Plan (Behavior Preserving)

Phase 0: Baseline and Safety Rails

Required before any code moves.
	•	Snapshot CLI help output for regression detection.
	•	Ensure these tests exist and are stable:
	•	CLI help snapshot unchanged
	•	mock.patch target resolution across tests
	•	import smoke for cihub, cihub.cli, cihub.commands.hub_ci, cihub.commands.report, cihub.services.ci_engine
	•	locked hub_ci command count (47)
	•	aggregate-report partial-data test (aggregation must render even if some repos fail)
	•	Inventory current imports of cihub.cli and define the “public facade list”.
	•	Document layering rules in this plan (done).

Progressive boundary enforcement begins here:
	•	Add AST boundary test enforcing utils purity only (details below).
	•	Do this before code moves, so you catch violations immediately.

Phase 1: Utilities Extraction (Low Risk)
	•	Create cihub/utils/env.py, progress.py, and move helpers without signature changes.
	•	Extract helpers into cihub/utils/:
	•	paths: hub_root, validate_repo_path, validate_subdir
	•	git: get_git_branch, get_git_remote, parse_repo_from_remote
	•	exec: resolve_executable, shared subprocess helpers
	•	github: gh_api_json, fetch_remote_file, etc
	•	java_pom: POM helper functions
	•	Extract CommandResult to cihub/types.py and re-export from cihub.cli.
	•	Update imports to use cihub/utils/* or cihub/types.
	•	Keep cihub.cli re-exports for all moved items.

No behavior changes allowed:
	•	preserve logging, stdout/stderr behavior, return codes, and error messaging.

Phase 2: Tool Registry Modularization (Medium Risk)
	•	Create cihub/tools/registry.py holding exact tool lists, order, and metric maps currently used.
	•	Preserve ordering and content exactly. No additions/removals.
	•	Update imports to use cihub.tools.registry.
	•	Add strict equality tests that enforce ordering and content.

Note:
	•	This is an internal tool registry only, separate from the future “registry feature” in your roadmap.

Phase 3: Commands Modularization (High Risk)

Phase 3a: Split commands/hub_ci.py (Strangler Approach)
	•	Extract groups into cihub/commands/hub_ci/*.py while keeping behavior identical.
	•	Keep helpers with their command group unless shared across groups.
	•	Preserve lazy imports inside command bodies (do not lift them).
	•	After extraction, convert hub_ci.py to package hub_ci/ in a single commit.
	•	Ensure cihub.commands.hub_ci still exposes all 47 cmd_* functions and required helpers.

Phase 3b: Split commands/report.py
	•	Extract into cihub/commands/report/*.py: build, aggregate, outputs, summary, validate, dashboard, helpers.
	•	Keep router in cihub/commands/report/__init__.py.
	•	Preserve signature differences and output formatting.
	•	Convert report.py to package report/ in a single commit.

Phase 4: Services Modularization (High Risk)
	•	Convert cihub/services/ci_engine.py to package ci_engine/ with facade __init__.py.
	•	Move python/java tool logic, gates, and IO helpers into submodules.
	•	Keep original function names and signatures available via cihub.services.ci_engine.
	•	Remove services -> cli imports by routing through cihub/utils.

Phase 5: Core Module Organization (Low Risk)
	•	Move root modules into cihub/core/:
	•	aggregation, ci_runner, ci_report, reporting, badges, correlation
	•	Keep facade modules at original paths with explicit __all__.

Phase 6: CLI Parser Modularization (Medium Risk)
	•	Extract parser setup into cihub/cli_parsers/* modules (parser-only, no handler imports).
	•	Keep stub handler functions in cihub/cli.py (lazy imports preserved).
	•	Use explicit registry ordering in cli.py to preserve --help ordering.

Phase 7: Config Loader Modularization (Medium Risk)
	•	Convert cihub/config/loader.py to package config/loader/.
	•	Split helpers into submodules.
	•	Keep cihub.config.loader import path stable via facade.
	•	Enforce canonical loader invariant and remove duplicate merge logic everywhere else via delegation.

Phase 8: Wizard and Diagnostics Tidying (Low Risk, Optional)
	•	Optional extraction into cihub/wizard/prompts.py and similar.
	•	Preserve prompts, defaults, and output formatting.

⸻

Progressive Boundary Enforcement (AST Tests)

Do not wait until the end.

Stage 1 (after Phase 0 or Phase 1):
	•	Enforce utils purity only:
	•	utils cannot import services/core/commands/cli/cli_parsers

Stage 2 (after Phase 3 or Phase 4):
	•	Expand to full layering enforcement:
	•	core cannot import commands/cli_parsers/cli
	•	services cannot import commands/cli
	•	commands can import services/core/utils
	•	cli can import anything

Keep it AST-based, no external dependency required.

⸻

Testing and Go/No-Go Gates (Every Phase)

Required for every phase commit:
	•	pytest tests/ (plus mutants/tests if applicable)
	•	CLI help snapshot unchanged
	•	mock.patch target resolution test
	•	aggregate-report partial-data test
	•	hub_ci command count lock (47)
	•	AST boundary test (stage-appropriate)
	•	No new circular imports (optional dev check)

⸻

Rollback Strategy
	•	One commit per phase.
	•	If a phase fails tests, revert that single commit and fix in isolation.

⸻

Operational Philosophy (Put This In AGENTS.md)
	•	The CLI is the product and source of truth. Workflows are thin wrappers.
	•	If GitHub Actions fails, an emergency YAML patch is allowed to unblock production.
	•	But the fix must be absorbed into CLI immediately, and locked with regression tests, so you never hand-edit YAML again.

⸻

Your Earlier Questions (Decisions)

Q1: Where does load_effective_config() live today, and who imports it?
	•	Treat this as a required Phase 0 inventory task: grep it, list call sites, and write down the signature expectations before refactoring.

Q2: Should the AST boundary test run in cihub check --audit or always?
	•	Always. Boundary violations are structural regressions, not optional audits. Make it part of default cihub check.

Q3: Contract spec location: YAML in schema/ vs Python dict in tests/?
	•	Start with a Python dict in tests to avoid creating a new parser layer while you are refactoring.
	•	Later, if you want it shareable across tooling, graduate it to YAML. Do not do that during modularization.

⸻

If you want, I can also rewrite this into a shorter “execution checklist” version (Phase-by-phase bullet checklist you can paste into your status doc).

Q1: Do you want the progressive AST boundary test to block PRs immediately, or start as warning for 1-2 commits then flip to fail?
Q2: Which module is currently the biggest “god file” you want to strangler first: cli.py, commands/hub_ci.py, or services/ci_engine.py?
Q3: Do you want to formalize a rule that every moved function must keep its original import path working for at least one release cycle (even internally), or can internal imports be migrated immediately?