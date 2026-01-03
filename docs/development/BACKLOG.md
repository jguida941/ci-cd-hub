# Backlog

Single queue for known issues and near-term work.

## High Priority

| Item                        | Category       | Notes                                                                                                            |
|-----------------------------|----------------|------------------------------------------------------------------------------------------------------------------|
| NVD key setup issue         | Secrets        | Possible whitespace/validation or missing secret propagation; `setup-nvd` may not work end-to-end (docs/development/CHANGELOG.md) |
| Phase 6: Diagnostics module | CLI            | `cihub/diagnostics/` scaffolded but not implemented (models.py, renderer.py, collectors/)                        |
| Token Permissions Hardening | Supply Chain   | Scorecard flagged 12 workflows missing explicit `permissions:` blocks; add to reusable workflow templates        |

## Medium Priority

| Item                                | Category       | Notes                                                              |
|-------------------------------------|----------------|--------------------------------------------------------------------|
| CLI: dispatch + sync in one command | CLI            | Combine dispatch repo update and workflow sync into single command |
| PyQt6 GUI ADR + MVP scope           | Planning       | Define ADR and minimal viable scope for GUI tool                   |
| CLI add/list/lint/apply commands    | CLI            | Partial implementation noted in ARCH_OVERVIEW.md                   |
| Restore relaxed thresholds          | Fixtures       | ADR-0018 notes some thresholds relaxed due to tool config issues   |
| Dependabot for Satellite Repos      | Supply Chain   | Extend dependabot.yml to Java/Python satellite repos; see ADR-0030 |

## Low Priority / Future

| Item                                  | Category       | Notes                                                              |
|---------------------------------------|----------------|--------------------------------------------------------------------|
| User-facing tool documentation        | Docs           | ADR-0017 lists as TODO                                             |
| Kotlin project support                | CLI            | Mentioned in RESEARCH_LOG.md as TODO                               |
| Validate configs against actual repos | Testing        | audit.md mentions this as incomplete                               |
| Fuzzing Support                       | Supply Chain   | Scorecard flagged; consider OSS-Fuzz for config parsing/validation |

## Might be stale or inaccurate

### Dependabot for Satellite Repos
**Priority**: Medium
**Added**: 2025-12-26
**Reference**: ADR-0030

Extend Dependabot configuration to satellite repositories using hub workflows:

- [ ] Java repos: Add Maven/Gradle ecosystem to dependabot.yml template
- [ ] Python repos: Add pip ecosystem to dependabot.yml template
- [ ] Create reusable dependabot.yml templates in `templates/`
- [ ] Document in guides how repos should adopt Dependabot

### Token Permissions Hardening
**Priority**: High
**Added**: 2025-12-26

Scorecard flagged 12 workflows for missing explicit `permissions:` blocks:

- [ ] Add `permissions: {}` (or minimal required) to all reusable workflow templates
- [ ] Audit each workflow for actual permission needs
- [ ] Update workflow templates in `templates/`

## Testing

### Fuzzing Support
**Priority**: Low
**Added**: 2025-12-26

Scorecard flagged missing fuzzing. Consider for critical parsing code:

- [ ] Evaluate OSS-Fuzz integration for config parsing
- [ ] Add fuzz tests for YAML/JSON schema validation

## Completed (Archive)

Move items here when done:

| Item                                 | Completed | PR/Commit |
|--------------------------------------|-----------|-----------|
| CLI modular restructure (Phases 1-5) | 2025-12   | -         |
| Wizard cancellation safety           | 2025-12   | -         |
