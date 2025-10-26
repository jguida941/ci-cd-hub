# CI Intelligence Hub

This repository implements the production-grade CI/CD platform defined in `plan.md`.

## Current focus

- Supply-chain enforcement (Kyverno policies, OCI referrers, Rekor proofs)
- Determinism tooling and data-quality/DR pipelines

Refer to `plan.md` for the complete architecture, roadmap, and v1.0 exit criteria.

## Development setup

Install the Python dependencies needed for local tooling/tests:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### Repairing unsigned container digests

All deployable images must carry a Cosign signature plus Rekor inclusion proof. If a previously published digest is missing its `.sig` manifest (for example, an image was built outside the release workflow), trigger the reusable `sign-existing-digest` workflow:

1. In GitHub → Actions → **sign-existing-digest**, click **Run workflow**.
2. Provide the image digest (`sha256:...`). The image field is optional and defaults to `ghcr.io/<owner>/ci-intel-app`.
3. The workflow logs in with OIDC, signs the digest with Cosign, runs `tools/rekor_monitor.sh` to capture the inclusion proof, and uploads the evidence bundle.

This keeps the Trust pillar of `plan.md` enforceable even when a manual repair is required.

### Mutation Observatory workflow

- Config: `mutation-observatory.ci.yaml`
- Run locally:

```bash
python tools/scripts/generate_mutation_reports.py \
  --stryker artifacts/mutation/stryker-report.json \
  --mutmut artifacts/mutation/mutmut-report.json

python tools/mutation_observatory.py \
  --config mutation-observatory.ci.yaml \
  --output artifacts/mutation/run.json \
  --ndjson artifacts/mutation/run.ndjson \
  --markdown artifacts/mutation/summary.md \
  --html artifacts/mutation/summary.html
```

GitHub Actions job `mutation-observatory` (see `.github/workflows/mutation.yml`) runs the same command on every push/PR, uploads the JSON/NDJSON/Markdown/HTML artifacts, and fails the build if the aggregate resilience drops below the configured thresholds. On pull requests the workflow automatically comments with the Markdown summary and a direct link to the HTML artifact so reviewers can inspect surviving mutants without digging through the Actions UI.
