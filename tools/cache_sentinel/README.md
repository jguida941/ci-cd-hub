# Cache Sentinel

## Purpose
Record and verify cache manifests (BLAKE3/SHA-256) to detect tampering or drift across builds.

## Usage
```bash
python tools/cache_sentinel.py record \
  --cache-dir "$(python -m pip cache dir)" \
  --output artifacts/evidence/cache/cache-manifest.json \
  --max-files 500

python tools/cache_sentinel.py verify \
  --cache-dir "$(python -m pip cache dir)" \
  --manifest artifacts/evidence/cache/cache-manifest.json \
  --quarantine-dir artifacts/evidence/cache/quarantine \
  --report artifacts/evidence/cache/cache-report.json
```

## Configuration
- `--max-files` controls sampling when recording.
- Verification reads the manifest’s `algorithm` (`blake3` or `sha256`).

## Testing
- Covered by release workflow; extend with unit tests in `tools/tests/test_cache_sentinel.py` as needed.

## Dependencies
- Python 3.12+
- `blake3` (optional; falls back to `hashlib.sha256`)

## Output & Artifacts
- Manifest: `artifacts/evidence/cache/cache-manifest.json`
- Report: `artifacts/evidence/cache/cache-report.json`
- Quarantined files: `artifacts/evidence/cache/quarantine/`

**Back to:** [Overview](../../docs/OVERVIEW.md) · [Testing](../../docs/TESTING.md) · [Module doc](../../docs/modules/cache_sentinel.md)
