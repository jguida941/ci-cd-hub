# Changelog

All notable changes to this project are recorded here. This file follows “Keep a Changelog” conventions and uses semantic version headings when tags are cut.

## [Unreleased]
### Added
- Repository-wide audit plan in `audit.md` describing the documentation cleanup and SoT map.
- Foundations for doc governance: ADR set under `docs/adr/`, backlog summary in `docs/backlog.md`, and this changelog.

## [v1.0.10] - 2025-11-02
### Added
- Documented supply-chain guardrails (SHA-pinned actions, cosign/Rekor/SBOM/VEX evidence bundle, determinism harness) and single-repo readiness snapshot (~85 %) in `README.md` and `docs/status/honest-status.md`.
- Captured multi-repo pilot posture (dynamic repo registry, proxy-based egress allowlists, per-repo timeouts) in archived `docs/status/archive/implementation-2025-11-02.md` and `docs/analysis/multi-repo-analysis.md`.

### Known gaps
- Per-repo secrets, fair scheduling/rate limiting, and cost/observability wiring remain in progress; see `docs/backlog.md` and status docs for current coverage.
