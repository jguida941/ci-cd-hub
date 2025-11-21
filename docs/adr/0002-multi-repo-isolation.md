# ADR-0002: Multi-Repo Isolation & Fairness Posture
Status: Accepted (in progress)
Date: 2025-11-02
Owners: Platform team

## Context
The hub now discovers repositories dynamically (`config/repositories.yaml`) and runs matrix jobs with per-repo timeouts and proxy-based egress allowlists. Hard isolation (per-repo secrets, fair scheduling, self-hosted runners) remains incomplete, yet README/status docs advertise multi-repo readiness. We need a documented posture and the required controls to reach production.

## Decision
- Treat current multi-repo support as pilot: logical segmentation only (matrix + proxy allowlists + per-repo timeout).
- To graduate to production, the following controls are mandatory:
  - Per-repo secret brokerage (GitHub App + Vault or equivalent) replacing the shared `GITHUB_TOKEN`.
  - Fair scheduling/token-bucket rate limiting with queue telemetry.
  - Optional but preferred: runner isolation (self-hosted with cgroups/Firecracker) for memory/CPU guarantees.
- Status reporting must align across README and `docs/status/honest-status.md`; deprecate redundant status narratives once aligned.

## Consequences
- Until the mandatory controls land, multi-repo runs are limited to trusted repositories; untrusted tenants are out of scope.
- Workflows and scripts must preserve per-repo egress configuration and timeout wiring; regressions are release blockers.
- Documentation must link to the canonical backlog/status for these controls (issues + `docs/backlog.md`), avoiding stale readiness claims.

## References
- docs/status/honest-status.md
- Historical snapshot: docs/status/archive/implementation-2025-11-02.md
- docs/analysis/multi-repo-analysis.md
- config/repositories.yaml, scripts/load_repository_matrix.py
