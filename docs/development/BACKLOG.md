# Backlog

Single queue for known issues and near-term work.

## High Priority

| Item                        | Category       | Notes                                                                                                            |
|-----------------------------|----------------|------------------------------------------------------------------------------------------------------------------|
| NVD key setup issue         | Secrets        | Possible whitespace/validation or missing secret propagation; `setup-nvd` may not work end-to-end (docs/development/CHANGELOG.md) |
| Phase 6: Diagnostics module | CLI            | `cihub/diagnostics/` scaffolded but not implemented (models.py, renderer.py, collectors/)                        |

## Medium Priority

| Item                                | Category       | Notes                                                              |
|-------------------------------------|----------------|--------------------------------------------------------------------|
| Token Permissions Hardening         | Supply Chain   | Reconfirm workflow `permissions:` coverage; pin `harden-runner`    |
| PyQt6 GUI ADR + MVP scope           | Planning       | Define ADR/minimal viable scope for GUI tool                       |
| Restore relaxed thresholds          | Fixtures       | ADR-0018 notes some thresholds relaxed due to tool config issues   |

## Low Priority / Future

| Item                                  | Category       | Notes                                                              |
|---------------------------------------|----------------|--------------------------------------------------------------------|
| Dependabot for Satellite Repos        | Supply Chain   | Extend dependabot.yml to satellite repos; see ADR-0030             |
| Kotlin project support                | CLI            | Mentioned in RESEARCH_LOG.md as TODO                               |
| Validate configs against actual repos | Testing        | audit.md mentions this as incomplete                               |
| Fuzzing Support                       | Supply Chain   | Scorecard flagged; consider OSS-Fuzz for config parsing/validation |

---

## New Backlog Items to Add (from current gaps)

| Item                                        | Category          | Notes                                                         |
|---------------------------------------------|-------------------|---------------------------------------------------------------|
| Implement `cihub docs stale`                | CLI/Docs          | Design in `docs/development/active/DOC_AUTOMATION_AUDIT.md`   |
| Implement `cihub docs audit` + manifest     | CLI/Docs          | Lifecycle/header checks, plain-text scan, `.cihub/tool-outputs` |
| Generate `docs/reference/TOOLS.md`          | Docs              | From `cihub/tools/registry.py` via `cihub docs generate`       |
| Generate `docs/reference/WORKFLOWS.md`      | Docs              | From `.github/workflows/*.yml`; guides stay narrative          |
| Consolidate `_tool_enabled()` helper        | Code quality      | Single helper + tests                                         |
| Gate-spec refactor                          | Code quality      | Declarative gates per language strategy                       |
| Expand CI engine tests                      | Testing           | Increase coverage in `tests/test_services_ci.py`               |
| Enforce `--json` for all commands           | CLI UX            | Contract test; include hub-ci subcommands                     |
| Pin `harden-runner` and unpinned actions    | Supply Chain      | Version pins across all workflows                             |


## Completed (Archive)

Move items here when done:

| Item                                 | Completed | PR/Commit |
|--------------------------------------|-----------|-----------|
| CLI modular restructure (Phases 1-5) | 2025-12   | -         |
| Wizard cancellation safety           | 2025-12   | -         |
