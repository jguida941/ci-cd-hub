# Requirements (v1.0)

**Status:** Active
**Last Updated:** 2026-01-05
**Owner:** Hub maintainers
**Sources:** `docs/development/MASTER_PLAN.md` (execution), `docs/development/status/STATUS.md` (current state)

---

## Status Legend
- `[ ]` Not started
- `[~]` Implemented but not fully verified
- `[x]` Verified complete
- `[!]` Blocked

---

## P0 Release Gates (Must Have)

### Central Execution (hub-run-all.yml)
- [~] Hub clones target repos and runs `cihub ci` per repo.
- [~] Per-repo `report.json` + `summary.md` are generated and uploaded.
- [~] Aggregated `hub-report.json` + optional details output produced.
- [~] Step summary includes core metrics and failure context.

### Config System
- [~] Config precedence enforced: repo `.ci-hub.yml` > hub config > defaults.
- [~] Schema validation fails fast on invalid configs.
- [~] Required repo fields (`repo.owner`, `repo.name`, `language`) enforced.

### Tool Toggles + Thresholds
- [~] Tool toggles follow `enabled: true/false` pattern across Java/Python.
- [~] Thresholds are configurable per tool and applied in reports.
- [~] Optional tool installs are explicit and surfaced as warnings when missing.

### Distributed Execution (hub-orchestrator.yml)
- [~] Dispatch respects `default_branch` and `dispatch_workflow` per repo.
- [~] Dispatch failures are surfaced (not fire-and-forget).
- [~] Run IDs are captured best-effort for aggregation.
- [~] Aggregation handles missing/failed runs gracefully.

### Documentation (Core)
- [x] CLI reference is generated from `cihub --help`.
- [x] Config reference is generated from the schema.
- [~] Tools/workflows references are generated (pending).
- [~] Guides are up to date with CLI-first behavior.

### Templates + Smoke Test
- [~] Repo templates are copy-paste ready and match the CLI outputs.
- [x] Smoke tests run successfully against Java + Python fixtures.

---

## P1 Targets (Should Have)

### ADR Coverage
- [~] ADRs cover core architectural decisions (status maintained).
- [~] ADR index is generated and linted for metadata.

### Documentation Depth
- [~] Tools documentation is generated from `cihub/tools/registry.py`.
- [~] Workflow triggers/inputs tables are generated from `.github/workflows/*.yml`.
- [~] Example configs cover common scenarios.

### Profile Templates
- [~] Java quality/security profiles exist and are validated.
- [~] Python quality/security profiles exist and are validated.

### Dashboard
- [~] `cihub report dashboard` generates HTML/JSON from aggregated reports.
- [ ] Optional publishing (GitHub Pages or equivalent) is documented.

### CLI Ergonomics
- [~] Config validation command exists (`cihub config validate` or equivalent).
- [~] CLI can apply profiles and enable/disable tools deterministically.
- [~] `--dry-run` is available on write operations.

### Distributed Mode Polish
- [~] Artifact download + correlation are stable in dispatch runs.
- [~] Aggregation merges results into a unified report with thresholds.

---

## Non-Functional Targets

### Performance
| Metric                         | Target   | Current | Status |
|--------------------------------|----------|---------|--------|
| Single repo CI (no mutation)   | < 15 min | Unknown | [ ]    |
| Single repo CI (with mutation) | < 30 min | Unknown | [ ]    |
| Config validation              | < 5 sec  | Unknown | [ ]    |
| Hub summary generation         | < 30 sec | Unknown | [ ]    |
| Dashboard page load            | < 3 sec  | Unknown | [ ]    |

### Reliability
| Metric                     | Target | Current | Status |
|----------------------------|--------|---------|--------|
| Config validation accuracy | 100%   | Unknown | [ ]    |
| Artifact upload success    | 99%+   | Unknown | [ ]    |
| Dispatch failure detection | 100%   | Unknown | [ ]    |

### Documentation Coverage
| Metric               | Target | Current | Status |
|----------------------|--------|---------|--------|
| Tools documented     | 100%   | Manual  | [~]    |
| Toggles documented   | 100%   | Manual  | [~]    |
| Workflows documented | 100%   | Manual  | [~]    |
| Templates commented  | 100%   | Manual  | [~]    |

---

## Notes
- These are outcome-focused requirements; the execution checklist lives in `MASTER_PLAN.md`.
- If an item is marked `[x]`, it should be verifiable via CLI output, tests, or CI artifacts.
