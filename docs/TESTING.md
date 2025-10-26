# Testing Matrix

| Suite | Command | Runs In | Notes |
| --- | --- | --- | --- |
| Tooling unit tests | `pytest tools/tests` | `tools-ci.yml`, local | Covers mutation observatory helpers, cache sentinel, provenance utilities. |
| Schema validation | `python scripts/validate_schema.py fixtures/pipeline_run_v1_2/*.ndjson` | `schema-ci.yml` | Ensures `pipeline_run.v1.2` compatibility before ingest. |
| Policy bundle | `opa test -v policies` | `release.yml` (policy-gates job) | Requires `policy-inputs/*` fixtures (SBOM, issuer, referrers). |
| Mutation synthetic workflow | `pytest tools/tests/test_mutation_observatory.py` | `mutation.yml` | Exercises diff thresholds and stale report logic. |
| Ingest dry run | `python ingest/chaos_dr_ingest.py --project fake --dataset tmp --chaos-ndjson artifacts/chaos.ndjson --dr-ndjson artifacts/dr.ndjson --dry-run` | local/ingest job | Verifies chaos/DR NDJSON parse + metadata injection without touching BigQuery. |
| Kyverno manifest check | `kyverno apply supply-chain-enforce/kyverno/verify-images.yaml --resource <sample manifest>` | `release.yml` / ops runbook | Confirms signed images + attestations satisfy policy before rollout. |

## Local Smoke Suite

```bash
python -m pip install -r requirements-dev.txt
pytest tools/tests
python scripts/validate_schema.py fixtures/pipeline_run_v1_2/sample.ndjson
python ingest/chaos_dr_ingest.py \
  --project demo --dataset ci_intel \
  --chaos-ndjson artifacts/evidence/chaos/events.ndjson \
  --dr-ndjson artifacts/evidence/dr/events.ndjson \
  --dry-run
opa test -v policies
```

To exercise the full release path locally, run `./scripts/install_tools.sh` once, then execute the relevant sections from `.github/workflows/release.yml` (syft → cosign → publish referrers). Capture the generated NDJSON artifacts and feed them to the ingest dry run above.

## MkDocs Preview

Documentation edits should pass `markdownlint` and render via MkDocs:

```bash
pip install mkdocs-material
cd docs
mkdocs serve
```

## Changelog
- 2025-10-26: Documentation framework initialized.
- 2025-11-14: Added ingest + Kyverno checks to the matrix.
