# Supply Chain Controls

## Signing & Provenance
- Builds use keyless cosign signing and emit SLSA v1.0 provenance.
- `tools/publish_referrers.sh` uploads CycloneDX/SPDX SBOMs and provenance as OCI 1.1 referrers and signs them.

## Rekor Monitoring
- `tools/rekor_monitor.sh` captures inclusion proofs for each release digest.
- Proofs are added to Evidence Bundles for auditability.

## Admission Policies
- `supply-chain-enforce/kyverno/verify-images.yaml` enforces digest allowlists, provenance, and SBOM referrers with deny-by-default.
- OPA policies (`policies/*.rego`) run in CI and admission to ensure issuer/subject allowlists and VEX coverage.
- `tools/build_issuer_subject_input.py` verifies the cosign signature for each release image and materializes the issuer/subject payload consumed by `policies/issuer_subject.rego`.

## Referrer Presence Gate
- Release workflow verifies required referrers (SPDX, CycloneDX, SLSA) via OPA before promotion.

## SBOM + VEX Policy Feed
- `build-sign-publish` now generates a CycloneDX VEX document via `tools/generate_vex.py`, sourced from `fixtures/supply_chain/vex_exemptions.json`, and stores it with the SBOM artifacts so it can be published as an OCI referrer.
- `policy-gates` downloads the CycloneDX SBOM, scans it with Grype, and runs `tools/build_vuln_input.py` to emit `policy-inputs/vulnerabilities.json`. Any VEX file found in the SBOM bundle (for example `app.vex.json`) is ingested automatically so documented `not_affected` findings satisfy `policies/sbom_vex.rego`.

## Determinism Evidence
- After publishing the image, the release workflow runs `tools/determinism_check.sh` against the immutable digest to capture the raw OCI manifest, a SHA256 over that manifest, and environment metadata. The resulting files live under `artifacts/evidence/determinism/` and prove what was pushed without relying on mutable tags.

## Base Image SLO
- Builds fail when base images introduce critical CVEs without VEX "not affected" evidence.
