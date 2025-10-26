# Rekor Monitor

## Purpose
Fetch Rekor log entries and inclusion proofs for a signed artifact digest, caching indices for faster lookups.

## Usage
```bash
./tools/rekor_monitor.sh \
  "sha256:<digest>" \
  "ghcr.io/org/image" \
  artifacts/evidence
```

## Configuration
- Environment:
  - `REKOR_LOG` (default `https://rekor.sigstore.dev`).
  - `REKOR_CLI_VERSION` to pin downloaded CLI.
- Requires `rekor-cli` and `jq` in PATH (script can download/pin CLI).

## Output & Artifacts
- Proof: `artifacts/evidence/rekor-proof-<timestamp>.json`
- Search results: `artifacts/evidence/rekor-search-<timestamp>.json`
- Cached indices: `artifacts/evidence/rekor-indices.txt`

## Testing
(Currently integration-tested via release workflow.)

## Dependencies
- Bash, curl, jq, rekor-cli.

## Changelog
- 2025-10-26: Documentation framework initialized.

## License
See [LICENSE](../../LICENSE).

**Back to:** [Overview](../../docs/OVERVIEW.md)
