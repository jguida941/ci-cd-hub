# Agents Catalog

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
