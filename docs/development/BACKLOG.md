# Backlog

**Status:** active
**Owner:** Development Team
**Source-of-truth:** manual
**Last-reviewed:** 2026-01-15

Single queue for known issues and near-term work.

## High Priority

| Item | Category | Notes |
|-----------------------------|----------|-----------------------------------------------------------------------------------------------------------------------------------|
| NVD key setup issue | Secrets | Possible whitespace/validation or missing secret propagation; `setup-nvd` may not work end-to-end (docs/development/CHANGELOG.md) |
| Phase 6: Diagnostics module | CLI | `cihub/diagnostics/` scaffolded but not implemented (models.py, renderer.py, collectors/) |

## Medium Priority

| Item | Category | Notes |
|-------------------------------------|----------------|--------------------------------------------------------------------|
| CLI env-var flag fallback | CLI | Allow common flags (`--owner`, `--repo`, `--bin`) to read from env vars. Started: `resolve_flag()` helper + kyverno/actionlint. Extend to remaining commands. |
| Token Permissions Hardening | Supply Chain | Reconfirm workflow `permissions:` coverage; pin `harden-runner` |
| PyQt6 GUI ADR + MVP scope | Planning | Define ADR/minimal viable scope for GUI tool |
| Restore relaxed thresholds | Fixtures | ADR-0018 notes some thresholds relaxed due to tool config issues |

## Low Priority / Future

| Item | Category | Notes |
|---------------------------------------|----------------|--------------------------------------------------------------------|
| Optional feature schemas (canary, chaos, etc.) | Schema | Full schema definitions for canary, chaos, dr_drill, egress_control, cache_sentinel, runner_isolation, supply_chain; tighten additionalProperties to false. Not needed until features are implemented. |
| Dependabot for Satellite Repos | Supply Chain | Extend dependabot.yml to satellite repos; see ADR-0030 |
| Validate configs against actual repos | Testing | audit.md mentions this as incomplete |
| Fuzzing Support | Supply Chain | Scorecard flagged; consider OSS-Fuzz for config parsing/validation |
| R-002-FOLLOWUP: split init detect/write | Architecture | Separate detection from write in `cihub init`; deferred from remediation |

---

## From ADR-0035 (Triage/Registry)

| Item | Category | Notes |
|---------------------------------------------|-------------------|---------------------------------------------------------------|
| Implement `cihub assist --prompt` | CLI/LLM | Generate LLM prompt pack from triage bundle |
| Implement `cihub fix --safe` | CLI | Auto-fix: ruff, black, isort, badges |
| Triage filtering flags | CLI | `--min-severity`, `--category` for triage output filtering |
| Formal JSON Schema for triage | Validation | `schema/triage.schema.json` for bundle validation |

## Other Backlog Items

| Item | Category | Notes |
|---------------------------------------------|-------------------|---------------------------------------------------------------|
| Deduplicate tasks across planning docs | Docs | 58 duplicate tasks detected across MASTER_PLAN.md, CLEAN_CODE.md, etc. (Part 13.S); re-enable in `consistency.py:validate_consistency()` when fixed |
| Generate `docs/reference/TOOLS.md` | Docs | From `cihub/tools/registry.py` via `cihub docs generate` |
| Vulnerability rollup in aggregation | Reporting | Aggregate vuln counts across repos in hub report (WORKFLOWS.md line 116) |
| Enforce `--json` for all commands | CLI UX | Contract test; include hub-ci subcommands |
| Pin `harden-runner` and unpinned actions | Supply Chain | Version pins across all workflows |


## Completed (Archive)

Move items here when done:

| Item | Completed | PR/Commit |
|--------------------------------------|-----------|-----------|
| CLI modular restructure (Phases 1-5) | 2025-12 | - |
| Wizard cancellation safety | 2025-12 | - |
| Implement `cihub registry` CLI | 2026-01 | list/show/set/diff/sync/add subcommands |
| Implement `cihub docs audit` | 2026-01 | ~80% complete, wired into `cihub check --audit` |
| Consolidate `_tool_enabled()` helper | 2026-01 | Canonical in `cihub/config/normalize.py` |
| Generate `docs/reference/WORKFLOWS.md` | 2026-01 | Auto-generated from `.github/workflows/*.yml` via `cihub docs generate` |
| Gate-spec refactor | 2026-01 | 27 ThresholdSpecs in gate_specs.py |
| Expand CI engine tests | 2026-01 | 2 -> 151+ tests |

---

## Future/Aspirational (Quarantine)

The following items from `_quarantine/phase11_docs/docs/backlog.md` are enterprise-grade features that may be added in the future but are not current priorities:

- Per-repo secret brokerage (GitHub App + Vault)
- Token-bucket rate limiting with Redis
- BigQuery telemetry dashboards
- Kyverno/OPA policy enforcement (audit -> enforce)
- OCI artifact signing and admission verification
- Cross-time determinism gating

These remain in quarantine for reference and may be revisited post-v1.0.
