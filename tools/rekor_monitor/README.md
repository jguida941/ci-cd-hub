# Rekor Monitor

## Purpose
Capture Rekor inclusion proofs for signed artifacts and surface verification results for CI gating.

## Usage
```bash
./tools/rekor_monitor.sh sha256:<digest> ghcr.io/<owner>/<image> artifacts/evidence/rekor
```

## Configuration
- Arguments: `<digest>` (sha256 of image), `<image>` (registry/repo), `<output-dir>` for evidence.
- Uses Rekor public log by default; set `REKOR_URL` to override.

## Testing
Covered in pipeline runs; add unit tests under `tools/tests/` if extending.

## Dependencies
- Bash, `rekor-cli`, `jq`.
- `rekor-cli` is auto-installed with checksum verification if absent.

## Output & Artifacts
- Rekor search/proof JSON files under `artifacts/evidence/rekor/`.

**Back to:** [Overview](../../docs/OVERVIEW.md) · [Testing](../../docs/TESTING.md)
