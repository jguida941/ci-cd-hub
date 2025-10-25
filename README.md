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
