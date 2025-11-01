# CI/CD Intelligence Hub – Agent Guide

The hub orchestrates release, security, and reliability automation across multiple downstream repositories (e.g., `learn-caesar-cipher`, `vector_space`). It packages every signal—from cache integrity to Rekor inclusion proofs—into a single promotion gate. This document gives the AI agents the context and intent behind the workflows defined in `plan.md`, and catalogs each automation component they will interact with.

## Operating Model & Scope

- **Mission**: deliver production-ready releases with verifiable supply-chain guarantees, deterministic builds, and policy-enforced deployments for every onboarded project.
- **Multi-repo hub**: the automation repo (`ci-cd-hub`) pulls source from other projects, runs their pipelines, and publishes shared telemetry/evidence artifacts.
- **Evidence-driven promotion**: the release workflow produces an evidence bundle (SBOM, VEX, provenance, Rekor proofs, cache manifests, determinism reports) that downstream promotion tooling must verify.
- **Telemetry everywhere**: each job emits NDJSON and artifacts under `artifacts/telemetry/` so the predictive scheduler, fairness analysis, and post-incident forensics have consistent data.

## Strategy & Roadmap (see `plan.md`)

| Phase | Focus | Highlights |
|-------|-------|------------|
| Phase 0 – Gate Integrity | Cache integrity, provenance verification, runtime secret sweeps, egress allowlists, Kyverno enforcement, Bandit gating | Cache manifest integrity ✅. Remaining blockers tracked in `issues.md` and `plan.md:60-90`. |
| Phase 1 – Hardening & Evidence | Evidence bundle attestation, DR freshness guard, SBOM parity, SARIF hygiene, LLM governance | Work in progress (`plan.md:88-120`). |
| Phase 2 – Extended Controls | KEV/EPSS SBOM diff, fairness budgets, cost/carbon telemetry, Dependabot automation, analytics tamper resistance | Backlog priorities (`plan.md:320+`). |

Agents should consult `plan.md` and `issues.md` before making changes; both files define priorities, blockers, and the 7-day/30-day action plans.

## Evidence & Telemetry Requirements

- **Cache manifests** (`plan.md:1633`): signed with cosign, verified before use, mismatches quarantined, telemetry emitted via `scripts/emit_cache_quarantine_event.py`.
- **Provenance** (`plan.md:34`): SLSA attestation generated; slsa-verifier enforcement is Blocker #3.
- **Rekor proofs**: `tools/rekor_monitor.sh` retrieves log entries and inclusion proofs; `tools/verify_rekor_proof.py` must succeed before release continues.
- **Policy gates**: OPA/Kyverno checks evaluate issuer/subject allowlists and SBOM/VEX coverage. Proof of enforcement remains outstanding.
- **Telemetry sinks**: NDJSON, logs, coverage summaries, and cache telemetry must be uploaded on success and failure for fairness/scheduler analytics.

## Outstanding Controls & Upcoming Work

Refer to `issues.md` for live tracking; key themes from `plan.md`:

- **Blockers**: runtime secret sweep, provenance verification (`slsa-verifier`), default-deny egress test, Kyverno enforcement evidence, Bandit gate hardening.
- **Hardening goals**: evidence bundle attestation, DR freshness guard, SBOM parity, SARIF dedupe, LLM governance policy, Dependabot/Renovate rollout.
- **Extended controls**: KEV/EPSS-aware SBOM diff, queue fairness budgets, cost/CO₂ telemetry enforcement, analytics tamper resistance, org-wide Rulesets.
- **Documentation gaps**: `docs/ENFORCEMENT_POSTURE.md`, `docs/CACHE_SECURITY.md`, `docs/ADMISSION_SETUP.md` still need to be authored after blockers close.

## Agent Collaboration Rules

1. **Align with plan**: Before editing workflows or scripts, confirm the change is on the critical path (Phase 0 blockers first, then Phase 1, etc.).
2. **Preserve evidence**: Never skip or delete artifact uploads without updating the evidence model and documentation.
3. **Document intent**: Update runbooks or this guide whenever behavior changes (e.g., new gate, new telemetry field).
4. **Validate with lint/tests**: Use `tools-ci` linting, targeted unit tests, and workflow dry-runs before merging modifications.

---

# Agent Catalog

This catalog describes each automation “agent” that runs inside the CI Intelligence Hub. Every entry lists purpose, trigger, inputs, outputs, gates, and a link to the relevant runbook or module README.

## Release Agent

- **Purpose**: Build, sign, and publish container images plus SBOM/VEX/provenance referrers.

- **Triggers**: Git tags (`v*.*.*`, `*.*.*`) via `.github/workflows/release.yml`.

- **Inputs**: Repository source, `fixtures/supply_chain/vex_exemptions.json`, cache manifests.

- **Outputs**: Multi-arch images, Cosign signatures, CycloneDX/SPDX SBOMs, CycloneDX VEX, SLSA provenance, evidence bundle.

- **Gates**: Cosign verification, Rekor monitor, policy gates (issuer/subject + SBOM/VEX).

- **Runbook**: [`docs/OVERVIEW.md`](./OVERVIEW.md) → Release Workflow section.

## Policy Gate Agent

- **Purpose**: Validate referrers, issuer/subject allowlists, and SBOM/VEX coverage.

- **Triggers**: `policy-gates` job inside release workflow.

- **Inputs**: `policy-inputs/referrers.json`, `policy-inputs/issuer_subject.json`, `policy-inputs/vulnerabilities.json`.

- **Outputs**: OPA evaluation logs, pass/fail status.

- **Gates**: Fails build on any missing referrer, issuer mismatch, or uncovered vulnerability.

- **Runbook**: `policies/README.md` (to be created).

## Mutation Observatory Agent

- **Purpose**: Capture mutation-test resilience and produce JSON/Markdown telemetry.

- **Triggers**: `.github/workflows/mutation.yml` on pushes/PRs.

- **Inputs**: Target config (`mutation_observatory.ci.yaml`), generated mutation reports.

- **Outputs**: `artifacts/mutation/run.json`, `run.ndjson`, `summary.md`.

- **Gates**: Fails if resilience < threshold or if required reports missing.

- **Runbook**: [`../tools/mutation_observatory/README.md`](../tools/mutation_observatory/README.md).

## Cache Sentinel Agent

- **Purpose**: Record and verify cache manifests to catch tampering.

- **Triggers**: Release workflow (record + verify), optional local invocation.

- **Inputs**: pip cache directory, manifest file.

- **Outputs**: `artifacts/evidence/cache/cache-manifest.json`, verification report, quarantined files.

- **Gates**: Blocks release if verification fails.

- **Runbook**: [`../tools/cache_sentinel/README.md`](../tools/cache_sentinel/README.md).

## Rekor Monitor Agent

- **Purpose**: Collect Rekor log entries/proofs for signed artifacts.

- **Triggers**: Release workflow evidence stage.

- **Inputs**: Image digest, registry subject.

- **Outputs**: `artifacts/evidence/rekor-proof-*.json`, cached indices.

- **Gates**: Alerts if UUID/log index lookup fails.

- **Runbook**: [`../tools/rekor_monitor/README.md`](../tools/rekor_monitor/README.md).

## Determinism Agent

- **Purpose**: Run determinism checks comparing build artifacts across runs.

- **Triggers**: Release workflow.

- **Inputs**: Image digest, reference builds.

- **Outputs**: `artifacts/evidence/determinism/*`.

- **Gates**: Fails on mismatched hashes or diffs.

- **Runbook**: `determinism-and-repro/README.md` (future).

## Chaos / DR Drill Agent

- **Purpose**: Execute disaster-recovery and chaos experiments (DR drill, chaos workflows).

- **Triggers**: `.github/workflows/chaos.yml`, `.github/workflows/dr-drill.yml`.

- **Inputs**: Chaos scenarios, DR scripts in `chaos/` and `determinism-and-repro/`.

- **Outputs**: `artifacts/chaos/*`, failure reproductions.

- **Gates**: Alerts on unmet RTO/RPO, surfaces to dashboards.

- **Runbook**: `chaos/README.md` and `determinism-and-repro/README.md`.

## Schema Compliance Agent

- **Purpose**: Validate JSON/NDJSON artifacts against schemas under `/schema`.

- **Triggers**: Included in tooling/unit test workflow.

- **Inputs**: Schema files, generated JSON/NDJSON.

- **Outputs**: pytest/CI logs highlighting schema violations.

- **Gates**: Blocks merges when schemas fail.

- **Runbook**: `schema/README.md` (future).

## SBOM/VEX Agent

- **Purpose**: Generate CycloneDX/SPDX SBOMs and CycloneDX VEX statements, publish as OCI referrers.

- **Triggers**: Release workflow.

- **Inputs**: Container image, `fixtures/supply_chain/vex_exemptions.json`.

- **Outputs**: `artifacts/sbom/app.cdx.json`, `app.spdx.json`, `app.vex.json`.

- **Gates**: Fails if SBOM/VEX generation or upload fails.

- **Runbook**: [`../tools/generate_vex/README.md`](../tools/generate_vex/README.md).

## Documentation Agent

- **Purpose**: Enforce markdown standards and aggregate module docs via MkDocs.

- **Triggers**: Tooling CI (markdownlint step) and optional doc build workflows.

- **Inputs**: Markdown files, `.markdownlint.json`, `docs/mkdocs.yml`.

- **Outputs**: Lint logs, MkDocs preview.

- **Gates**: CI fails if docs contain lint errors or TODO placeholders.

- **Runbook**: [`docs/OVERVIEW.md`](./OVERVIEW.md) & `docs/documentationupdate.md`.

## Changelog

- 2025-10-26: Documentation framework initialized.
