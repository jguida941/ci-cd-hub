# CLI Modularization Plan - Refined (v2)
> **Superseded by:** [MASTER_PLAN.md](../MASTER_PLAN.md)  

> **WARNING: SUPERSEDED** - This plan was executed and completed on 2026-01-03/04.
> See [MASTER_PLAN.md](../MASTER_PLAN.md) for current execution status and [status/STATUS.md](../status/STATUS.md) for ongoing work.
> Archived to [archive/Jan3.md](archive/Jan3.md).

Turn cihub/cli.py from a "utility dumping ground" into a thin facade while keeping every import path and CLI behavior stable.

 Key Principles

1. Move implementations, keep re-exports. Zero breakage.
2. cli.py is NOT a lower layer - others should not import from it long-term
3. No import-linter yet - finish extractions first, then enforce

 Status (2026-01-03)

 - [x] Batch A complete (delete_remote_file in utils/github_api + cli re-export)
 - [x] Batch B complete (write_text in utils/fs, safe_urlopen in utils/net + cli re-exports)
 - [x] Batch C complete (load_effective_config delegates to validated loader; detect/resolve in services/detection)
 - [x] Batch D complete (repo catalog + templates live in services/*, cli re-exports)
 - [x] Batch E complete (layer boundary tests in tests/test_module_structure.py)
 - [ ] Commit CLI helpers

 Existing Debug Modes (Already Implemented!)

 - CIHUB_DEBUG=True → Show tracebacks (cli.py)
 - CIHUB_VERBOSE=True → Show tool output (core/ci_runner/shared.py)
 - CIHUB_DEBUG_CONTEXT=True → Show context blocks (utils/debug.py)

 Correct Layering (Target)

 cli.py, cli_parsers/*, commands/* (entry points - depend on everything below)
 ↓
 services/* (business logic)
 ↓
 core/* (domain logic, tool runners)
 ↓
 utils/* (pure helpers - NO imports from above)

 ---
 What Already Exists (Don't Duplicate!)

 | Module | Has | Missing |
 |---------------------------|----------------------------------------------------|--------------------|
 | utils/github_api.py | fetch_remote_file, update_remote_file, gh_api_json | delete_remote_file |
 | utils/env.py | env_bool, env_str, _parse_env_bool | - |
 | utils/debug.py | debug_context_enabled, emit_debug_context | - |
 | config/loader/core.py | load_config() with schema validation | - |
 | services/configuration.py | load_repo_config, resolve_tool_path | - |
 | services/discovery.py | discover_repositories (advanced) | - |
 | services/types.py | RepoEntry dataclass, ServiceResult | - |

 NOTE: cihub/templates.py does NOT exist - safe to create services/templates.py

 ---
 Extraction Batches (Ordered by Risk)

 Batch A: Low Risk - Fill Existing Module

 1. Add delete_remote_file to utils/github_api.py
 - Copy from cli.py:422-435
 - Add re-export in cli.py
 - Uses existing gh_api_json helper

 Batch B: Low Risk - Create Utils

 2. Create utils/io.py with write_text
 - Move from cli.py:64-71
 - Add re-export in cli.py
 - Pure I/O helper, no dependencies

 3. Create utils/http.py with safe_urlopen
 - Move from cli.py:121-125
 - Add re-export in cli.py
 - Pure HTTP helper

 Batch C: Medium Risk - Service Extraction

 4. Create services/detection.py
 - Move detect_language from cli.py:74-94
 - Move resolve_language from cli.py:198-205
 - Add re-exports in cli.py

 5. Refactor load_effective_config to delegate to validated loader
 - Current cli.py version does NOT use schema validation
 - Must delegate to config/loader/core.py::load_config()
 - Add re-export in cli.py
 - CRITICAL: No duplicate merge logic!

 Batch D: Medium Risk - Domain Services

 6. Create services/catalog.py
 - Move get_connected_repos from cli.py:326-360
 - Move get_repo_entries from cli.py:363-401
 - Uses existing RepoEntry dataclass from services/types.py
 - Add re-exports in cli.py

 7. Create services/templates.py
 - Move render_caller_workflow from cli.py:183-195
 - Move render_dispatch_workflow from cli.py:404-414
 - Move build_repo_config from cli.py:152-180
 - Add re-exports in cli.py
 - Active callers: init.py, update.py, templates.py (NOT legacy)

 Batch E: Architecture Enforcement (DEFERRED)

 8. Add simple import boundary test (NOT import-linter yet)
 - After A-D complete, add test: "utils cannot import services/core/commands/cli"
 - Use ast scanning, not external tool
 - import-linter can be added later when layering is proven clean

 ---
 Files to Modify

 Existing Files (ADD to)

 - cihub/utils/github_api.py - add delete_remote_file
 - cihub/cli.py - convert to facade with re-exports

 New Files (CREATE)

 - cihub/utils/io.py - write_text
 - cihub/utils/http.py - safe_urlopen
 - cihub/services/detection.py - language detection
 - cihub/services/catalog.py - repo catalog functions
 - cihub/services/templates.py - template rendering

 Files NOT Changed (Removed from plan per ChatGPT feedback)

 - ~~`cihub/utils/env.py~~ - is_debug_enabledis justenv_bool("CIHUB_DEBUG", False)` - use directly
 - ~~`.importlinter`~~ - deferred until layering is clean

 ---
 Safety Rules

 1. One batch at a time - Run ruff check + mypy + pytest after each batch
 2. Always re-export - Keep from cihub.cli import X working
 3. Don't change signatures - Same names, same params, same return types
 4. Test smoke - Run python -m cihub --help after each batch

 ---
 Critical Constraint: Config Validation

 Problem: cli.py's load_effective_config() does NOT use schema validation.  
 Solution: It must delegate to config/loader/core.py::load_config() which DOES validate.

 # WRONG (current cli.py - no validation)
 def load_effective_config(repo_path):
 defaults = load_yaml_file(defaults_path)
 local = load_yaml_file(local_path)
 return deep_merge(defaults, local) # No schema check!

 # RIGHT (must delegate)
 def load_effective_config(repo_path):
 from cihub.config.loader.core import load_config
 return load_config(repo_name, hub_root, repo_path) # Uses jsonschema!

 ---
 Execution Approach

 One batch at a time with approval:
 1. Execute Batch A → Run tests → Get approval
 2. Execute Batch B → Run tests → Get approval
 3. Execute Batch C → Run tests → Get approval
 4. Execute Batch D → Run tests → Get approval
 5. Execute Batch E (simple ast test) → Done

 After each batch:
 - Show what was moved
 - Run ruff check cihub/ + mypy cihub/ + pytest tests/
 - Run python -m cihub --help smoke test
 - Wait for user approval before next batch

 ---
 After Completion

 cli.py contains ONLY:
 - build_parser() - parser construction
 - main() - entry point + error handling
 - cmd_* thin wrappers - delegators to commands
 - Re-exports for backward compat

 All business logic lives in services/*.

 Note: Don't target a line count. Target correct separation of concerns.

 ---
 Findings from Exploration

 Q: Does cihub/templates.py exist?
 → NO - safe to create services/templates.py

 Q: Which commands call render_ functions?*
 → Active paths (NOT legacy):
 - commands/templates.py (sync-templates)
 - commands/init.py (init)
 - commands/update.py (update)

 Q: Where is schema validation?
 → config/loader/core.py::load_config() uses jsonschema
 → Used by: services/configuration.py, commands/hub_ci/validation.py
 → NOT used by: cli.py's load_effective_config (this is the bug!)

 Q: Do init/update generate workflow files?
 → YES - init.py calls render_caller_workflow() at line 146
 → This is ACTIVE, not legacy

 ---
 Engineering Principles (Add to AGENTS.md)

 Core Objective

 The CLI is the product and source of truth. Workflows are thin wrappers.
 If something breaks in GitHub Actions, apply minimal YAML patch as emergency stopgap,
 then absorb the fix into CLI so we never hand-edit YAML again.

 Engineering Goals

 - Prioritize maintainability, scalability, simplicity
 - Clean code: docstrings, type hints, meaningful names
 - Modularization with clear boundaries: CLI → services → core → utils
 - Encapsulation: shared logic in one place, not duplicated
 - Polymorphism where it removes branching (ex: PythonEngine/JavaEngine)

 Process Rules

 - One batch at a time. No big bang refactors.
 - Keep CLI surface stable: no signature changes, no behavior changes
 - After every change: run ruff + mypy + pytest + smoke test
 - Any refactor must be proven by regression tests

 Testing Requirements (Non-Negotiable)

 Must produce CLI audit + test matrix:
 1. Enumerate every CLI command and subcommand
 2. For each: contract, inputs/flags, outputs/artifacts, exit codes, failure modes
 3. Regression tests that simulate real user flows (not just unit tests)
 4. Run flows across 10-30 fixture variations to prove stability

 When Commands Fail

 DO NOT "fix it in YAML." Instead:
 1. Diagnose using triage outputs
 2. Fix CLI/core/services logic
 3. Rerun command as user would
 4. Confirm it passes and stays passing via tests

 ---
 Gate for "Done"

 Modularization is NOT done until:
 1. All batches A-E complete
 2. CLI audit document exists with all commands documented
 3. Regression test suite covers real user flows
 4. Tests pass consistently (10+ runs)

 ---
 Testing & Audit Strategy (User Decisions)

 Contract Spec (Single Source of Truth)

 - Create machine-readable contract spec (YAML or Python dict)
 - Lists every command, flags, env toggles, artifacts, exit codes
 - Generate CLI_COMMAND_AUDIT.md FROM the spec
 - Drive pytest suite FROM the same spec
 - Zero drift - docs and tests share one source

 Fixture Strategy

 Default (always in CI): Generated fixtures via cihub scaffold
 - Deterministic, fast, stable
 - Hard regression gate

 Optional (nightly/manual): Real repos
 - Behind flag: CIHUB_REAL_REPOS=True
 - Separate workflow job: integration-real-repos
 - On failure: produce triage bundle, fix CLI

 Fixture Registry (repo scenarios):
 - python-pyproject-minimal
 - python-pyproject-with-docker
 - java-maven-single
 - java-maven-parent-child
 - java-maven-multi-module-with-bom
 - mixed-java-python-root
 - monorepo-subdir-python
 - repo-with-existing-workflows
 - repo-with-broken-config (expected failure)

 Failure Output (Non-Negotiable)

 On ANY failure, CLI must produce:
 - .cihub/triage.json (machine-readable, stable schema)
 - .cihub/triage.md (LLM prompt pack)
 - .cihub/priority.json (sorted blockers)
 - .cihub/artifacts/<tool>/stdout.log
 - .cihub/artifacts/<tool>/stderr.log
 - .cihub/artifacts/<tool>/exit_code
 - .cihub/artifacts/<tool>/command.json

 Context in triage:
 - Command invoked, cwd, repo path
 - Resolved config sources and paths
 - Toggle decisions per tool (enabled/disabled + reason)
 - Versions: cihub, python, OS, git sha

 Layer Enforcement (Full)

 AST boundary test checks ALL layers:
 - utils cannot import services/core/commands/cli
 - core cannot import commands/cli_parsers
 - services cannot import cli/commands

 ---
 AGENTS.md Update Required

 Add new section with engineering principles:
 - CLI is product, workflows are thin wrappers
 - Emergency YAML patch allowed, must be absorbed into CLI
 - Modularization boundaries
 - Testing requirements
 - Failure handling philosophy
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
