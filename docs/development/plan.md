# CI/CD Hub Development Plan

> **Single source of truth** for project status, priorities, and remaining work.
>
> **See also:** `REUSABLE_WORKFLOW_MIGRATION.md` for detailed technical implementation.
>
> **Last Updated:** 2025-12-23
> **Version Target:** v1.0.0

---

## Current Status

### What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| Central Mode (`hub-run-all.yml`) | **PASSING** | Full tool coverage, 5m35s runs |
| Reusable Workflows | Working | `python-ci.yml`, `java-ci.yml` with `workflow_call` |
| Caller Templates | Working | `hub-python-ci.yml`, `hub-java-ci.yml` |
| Schema Validation | Working | `config-validate.yml` workflow |
| CLI Tool (`cihub`) | **v0.2.0** | 6 commands: detect/init/update/validate/setup-secrets/setup-nvd |
| Tests | **80 tests** | 6 test files covering all scripts |
| ADRs | **20 ADRs** | 0001 through 0020 complete |
| Smoke Test | **PASSING** | Last run: 2025-12-22 |

### What's Broken

| Component | Status | Issue |
|-----------|--------|-------|
| Hub Orchestrator | **FAILING** | Schedule and push triggers failing (needs investigation) |
| Hub Security | **FAILING** | Security workflow also failing |

### Workflow Health (2025-12-23)

```
Hub: Run All Repos     PASSING  (5m35s)
Smoke Test             PASSING  (1m30s)
Hub Self-Check         PASSING  (20s)
Validate Hub Configs   PASSING  (13s)
Hub Orchestrator       FAILING  (schedule + push)
Hub Security           FAILING
```

---

## P0 Checklist (Ship-Ready)

All P0 items complete. See `requirements/P0.md` for details.

- [x] Central mode clones and tests repos
- [x] Java CI (Maven/Gradle support)
- [x] Python CI (pytest, coverage)
- [x] Config hierarchy (defaults → repo config → .ci-hub.yml)
- [x] Schema validation (fail fast on bad YAML)
- [x] Step summaries with metrics
- [x] Artifact uploads
- [x] Documentation (WORKFLOWS, CONFIG_REFERENCE, TOOLS, TEMPLATES, MODES, TROUBLESHOOTING)
- [x] Templates (12 profiles: java/python × minimal/fast/quality/coverage-gate/compliance/security)
- [x] Smoke test verified

**P0 Blockers:** None

---

## P1 Checklist (Should-Have)

- [x] ADRs: 20 complete (0001-0020)
- [x] Profiles/templates: 12 profiles complete
- [x] Fixtures: `ci-cd-hub-fixtures` repo with 4 configs (java/python passing/failing)
- [x] CLI: `cihub` v0.1.0 with detect/init/update/validate/setup-secrets
- [ ] CLI: validate `setup-secrets` token trim/verify with a real dispatch run
- [ ] Dashboard: GitHub Pages site (HTML exists, needs deployment)
- [x] Orchestrator fix: Input passthrough complete (mutation_score_min, run_hypothesis, run_jqwik, all max_* thresholds)
- [ ] Refactor: Move inline Python from workflows to scripts/
- [ ] Composite actions: Reduce java-ci.yml + python-ci.yml duplication
- [ ] CODEOWNERS: Protect workflows/config/schema/templates
- [ ] Integration tests: `act` or similar for workflow testing

---

## Blocking Issues for v1.0.0

### 1. Hub Orchestrator Failing

**Impact:** Distributed mode doesn't work reliably.

**Note:** Input passthrough is COMPLETE (mutation_score_min, run_hypothesis, run_jqwik, all max_* thresholds are passed). The failure is something else - needs investigation.

### 2. Hub Security Workflow Failing

Security scan workflow also failing. Needs investigation.

### 3. Report Schema ✅ Complete

All fields now implemented:
- `tools_ran` includes hypothesis (Python) and jqwik (Java)
- `tool_metrics` includes mypy_errors
- Schema version 2.0 emitted by both workflows

---

## Project Context (Condensed from `docs/development/archive/ROADMAP.md`)

### Vision & Core Principles

**Vision:** A user-friendly CI/CD template repo that can run pipelines for any language with easy-to-change templates and boolean toggles.

**Principles:**
- Repos stay clean (central mode default)
- Config-driven behavior (YAML, not workflow edits)
- Template-driven onboarding
- Boolean toggles for tools
- Sensible defaults

### Target Users
- Repo owners who want standard CI without writing workflows
- Engineering leads who want consistent policy across repos
- Students/learners who want a working CI/CD example
- DevOps engineers who want centralized control and visibility

### Requirements Summary

#### Functional Requirements
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Hub clones and tests repos without workflow files in target repos | P0 | Implemented |
| FR-02 | Support Java projects (Maven/Gradle) | P0 | Implemented |
| FR-03 | Support Python projects | P0 | Implemented |
| FR-04 | Per-tool boolean toggles (`enabled: true/false`) | P0 | Implemented |
| FR-05 | Per-repo config overrides | P0 | Implemented |
| FR-06 | Global defaults with config hierarchy | P0 | Implemented |
| FR-07 | Step summary with metrics table | P0 | Implemented |
| FR-08 | Upload artifacts (coverage, reports) | P0 | Implemented |
| FR-09 | Distributed mode (dispatch to repos) | P1 | Partial (orchestrator failing) |
| FR-10 | Real aggregation across repos | P1 | Partial (orchestrator failing) |
| FR-11 | GitHub Pages dashboard | P2 | Not started (HTML exists) |
| FR-12 | Comprehensive documentation | P1 | Implemented |
| FR-13 | Template files with heavy comments | P1 | Implemented |
| FR-14 | ADR documentation | P1 | Implemented |

#### Non-Functional Requirements (Targets)
| ID | Requirement | Target | Notes |
|----|-------------|--------|-------|
| NFR-01 | Single repo CI run completes in < 15 min (without mutation) | < 15 min | Hub-run-all ~5m35s (central, 2025-12-23) |
| NFR-02 | Config validation fails fast with clear error | < 5 sec | Track via `config-validate.yml` runtime |
| NFR-03 | Documentation covers all tools and toggles | 100% | See `docs/reference/TOOLS.md` + `docs/reference/CONFIG_REFERENCE.md` |
| NFR-04 | Templates are copy/paste ready | No edits beyond repo name | See `templates/` and `templates/README.md` |

### Tool Support Summary (Toggle Keys)

**Java Tools**
| Tool | Toggle Key | Notes |
|------|------------|-------|
| JUnit | Built-in | Test framework (no toggle) |
| JaCoCo | `java.tools.jacoco.enabled` | Coverage |
| Checkstyle | `java.tools.checkstyle.enabled` | Lint |
| SpotBugs | `java.tools.spotbugs.enabled` | Static analysis |
| PMD | `java.tools.pmd.enabled` | Static analysis |
| OWASP DC | `java.tools.owasp.enabled` | Dependency scan |
| PITest | `java.tools.pitest.enabled` | Mutation testing |
| jqwik | `java.tools.jqwik.enabled` | Property-based testing |
| CodeQL | `java.tools.codeql.enabled` | SAST |
| Semgrep | `java.tools.semgrep.enabled` | SAST (expensive; off by default) |
| Trivy | `java.tools.trivy.enabled` | Scan (expensive; off by default) |
| Docker | `java.tools.docker.enabled` | Optional docker checks |

**Python Tools**
| Tool | Toggle Key | Notes |
|------|------------|-------|
| pytest + coverage | `python.tools.pytest.enabled` | Coverage runs with pytest |
| Ruff | `python.tools.ruff.enabled` | Lint |
| Black | `python.tools.black.enabled` | Formatting |
| isort | `python.tools.isort.enabled` | Imports |
| Bandit | `python.tools.bandit.enabled` | Security |
| pip-audit | `python.tools.pip_audit.enabled` | Dependency scan |
| mypy | `python.tools.mypy.enabled` | Type checking |
| mutmut | `python.tools.mutmut.enabled` | Mutation testing |
| Hypothesis | `python.tools.hypothesis.enabled` | Runs with pytest |
| CodeQL | `python.tools.codeql.enabled` | SAST |
| Semgrep | `python.tools.semgrep.enabled` | SAST (expensive; off by default) |
| Trivy | `python.tools.trivy.enabled` | Scan (expensive; off by default) |
| Docker | `python.tools.docker.enabled` | Optional docker checks |

Full tool details: `docs/reference/TOOLS.md` and `docs/reference/CONFIG_REFERENCE.md`. Historical full matrix: `docs/development/archive/ROADMAP.md`.

### Success Criteria (Targets)

**MVP (baseline):**
- Central execution works for Java and Python
- All tools have boolean toggles
- Documentation covers all tools
- Templates are copy/paste ready
- ADRs captured for key decisions

**v1.0.0 (release targets):**
- Distributed mode works
- Fixtures tested
- Dashboard live
- CHANGELOG maintained

**Metrics to Track:**
| Metric | Target |
|--------|--------|
| Docs coverage | 100% of tools documented |
| Template usability | Copy/paste in < 5 min |
| CI run time | < 15 min without mutation |
| Onboarding time | New repo added in < 10 min |

### Risk Register (Condensed)
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Distributed mode too complex | High | Medium | Keep central as default, distributed optional |
| Too many tools to document | Medium | High | Prioritize P0 tools first |
| Dashboard scope creep | Medium | Medium | Start with static JSON, iterate |
| Breaking changes to workflows | High | Low | Version workflows, semantic versioning |
| Config schema changes | Medium | Medium | Schema validation, migration docs |

---

## Product Specs (Condensed)

### CLI Spec (Current + Roadmap)

**Current (v0.1.0):**
- `detect`, `init`, `update`, `validate`, `setup-secrets`

**Roadmap (from archived ROADMAP):**
- `repo`: add, list, show, remove, validate
- `config`: lint, show, generate, diff
- `profile`: list, show, apply
- `run`: all, single
- `docs`: render, serve
- Optional: interactive prompts, `--dry-run`, pip packaging

**Note:** Roadmap structure predates the current `cihub` CLI; reconcile naming and scope before expanding.

### CLI Onboarding UX (Planned v0.2)

**Goal:** one command to scan a repo, prompt for toggles/thresholds, and write the right configs.

**Proposed flow:**
1. Detect language(s) + repo layout (monorepo/subdir)
2. Select mode: central, distributed, or both
3. Select profile (optional), then override tool toggles
4. Set thresholds (coverage/mutation + max_* limits)
5. Write outputs:
   - `.ci-hub.yml` (repo-local override)
   - `.github/workflows/hub-ci.yml` (caller)
   - `config/repos/<repo>.yaml` (hub-side config for orchestrator, if requested)

**Implementation gaps:**
- Tool detection (pyproject/pom/gradle) to preselect toggles
- Profile integration in CLI
- Hub config generation/update
- Optional repo URL cloning
- `cihub diff`/`cihub sync` for upgrades

### Dashboard Requirements
- Static GitHub Pages dashboard
- Overview page with all repos
- Drill-down per repo
- Trend charts
- Auto-updates on each hub run
- Shows coverage, mutation, and security metrics

### Future Roadmap (v1.1.0+ Ideas)
- PyQt6 GUI
- Additional languages (Node, Go, Rust)
- Real-time dashboard
- Slack/Teams notifications
- Load testing tools (k6, Locust)

---

## Architecture

### Config Hierarchy (Highest Wins)

```
1. Repo's .ci-hub.yml        ← Highest priority
2. Hub's config/repos/<repo>.yaml
3. Hub's config/defaults.yaml ← Lowest priority
```

### Two Operating Modes

| Mode | Description | Status |
|------|-------------|--------|
| **Central** | Hub clones repos, runs tests directly | **Default, Working** |
| **Distributed** | Hub dispatches to repo workflows | Partial (orchestrator issues) |

### Open Decisions / Gaps

- Repo-local `.ci-hub.yml` is **not** currently consumed by hub workflows (they only read `config/repos/*.yaml`). Decide whether to:
  - implement repo-local override merge at runtime, or
  - treat hub config as the runtime source of truth and update docs/CLI accordingly.
- `extra_tests` config exists but hub workflows do not execute those commands; decide to wire it into `hub-run-all.yml` or deprecate the feature.

### ADRs

20 ADRs document all major decisions. See `docs/adr/README.md`.

Key decisions:
- ADR-0001: Central mode is default
- ADR-0002: Config precedence (repo wins)
- ADR-0014: Reusable workflow migration
- ADR-0019: Report validation policy
- ADR-0020: Schema backward compatibility

---

## Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| `test_config_pipeline.py` | 5 | Config loading |
| `test_apply_profile.py` | 19 | Profile merging |
| `test_templates.py` | 16 | Template validation |
| `test_aggregate_reports.py` | 28 | Report aggregation |
| `test_cihub_cli.py` | 7 | CLI functions |
| `test_contract_consistency.py` | 5 | Schema contracts |
| **Total** | **80** | |

Run: `pytest tests/`

---

## Testing Strategy (Required for CLI v0.2)

**Fixture matrix:**
- Python: `pyproject.toml` (poetry), `requirements.txt` (classic), `src/` layout, no tests
- Java: Maven, Gradle, multi-module
- Monorepo: mixed languages with subdir configs
- Edge cases: both Java+Python markers, no markers (expect failure), repo without git remote

**CLI e2e:**
- `detect` on each fixture (language + reasons)
- `init` on fresh repo (creates `.ci-hub.yml` + `hub-ci.yml`)
- `update` on existing repo (idempotent, preserves user edits)
- `validate` against schema
- Interactive prompt flows with scripted stdin + golden outputs

**Config contract tests:**
- Precedence: defaults < hub config < repo config
- `thresholds.*` overrides tool `min_*`
- Tool toggles map to workflow inputs

**Template validation:**
- `actionlint` on caller workflows
- Schema validation for generated configs

**Workflow smoke (optional):**
- `hub-run-all` and `hub-orchestrator` against fixtures

---

## Scripts

| Script | Purpose | Documented |
|--------|---------|------------|
| `load_config.py` | Load/merge configs | Yes |
| `validate_config.py` | Schema validation | Yes |
| `aggregate_reports.py` | Report aggregation | Yes |
| `apply_profile.py` | Apply profile to config | Yes |
| `verify_hub_matrix_keys.py` | Matrix key verification | Partial |
| `debug_orchestrator.py` | Debug artifact downloads | Yes |

---

## Remaining Work (Priority Order)

### High Priority
1. **Fix Hub Orchestrator** - Investigate why schedule/push triggers fail
2. **Fix Hub Security** - Investigate why security workflow fails
3. **Dashboard deployment** - GitHub Pages setup

### Medium Priority
4. **CLI onboarding v0.2** - Interactive prompts, profile selection, thresholds, mode selection, hub config output
5. **CLI completion** - Add `add`, `list`, `lint`, `apply` commands
6. **CLI e2e tests** - Fixture matrix + golden outputs for `init`/`update`
7. **Composite actions** - Reduce workflow duplication
8. **CODEOWNERS** - Protect critical paths

### Low Priority
9. **Integration tests** - Workflow testing with `act`
10. **Docker templates** - Separate `hub-*-docker.yml` (deferred to v1.1.0)

---

## v1.0.0 Scope

**Included:**
- Reusable workflows (`python-ci.yml`, `java-ci.yml`, `kyverno-ci.yml`)
- Caller templates (`hub-python-ci.yml`, `hub-java-ci.yml`)
- Report schema 2.0
- CLI v0.1.0 (`cihub`) with 5 commands
- 80 tests across 6 files
- 20 ADRs

**Deferred to v1.1.0:**
- Dashboard/GitHub Pages
- Docker templates
- CLI `add/list/lint/apply` commands
- Full fixture expansion (16+ planned)

---

## Quick Links

| Resource | Path |
|----------|------|
| Requirements | `requirements/P0.md`, `requirements/P1.md` |
| ADRs | `docs/adr/` |
| Historical Roadmap (archived) | `docs/development/archive/ROADMAP.md` |
| Schema | `schema/ci-hub-config.schema.json` |
| Fixtures | `ci-cd-hub-fixtures` repo |
| Smoke Test | `docs/development/SMOKE_TEST_SETUP_SUMMARY.md` |

---

## Notes

- Keep checkboxes honest - only mark `[x]` after verification
- AGENTS.md should reflect current focus from this plan
- Run smoke test after significant workflow changes
