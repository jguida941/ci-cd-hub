# Build Vulnerability Input

## Purpose
Normalize Grype scan results (plus optional VEX) into OPA-friendly JSON for `policies/sbom_vex.rego`.

## Usage
```bash
python tools/build_vuln_input.py \
  --grype-report policy-inputs/grype-report.json \
  --output policy-inputs/vulnerabilities.json \
  --cvss-threshold 7.0 \
  --epss-threshold 0.75 \
  --vex artifacts/sbom/app.vex.json
```

## Configuration
- Thresholds determine which vulnerabilities require VEX coverage.
- `--vex` is optional but recommended to include release VEX.

## Testing
```bash
pytest tools/tests/test_build_vuln_input.py
```

## Dependencies
- Python 3.12+
- `pyyaml`, `jsonschema`

## Output & Artifacts
- Normalized input: `policy-inputs/vulnerabilities.json`

**Back to:** [Overview](../../docs/OVERVIEW.md) · [Testing](../../docs/TESTING.md) · [Module doc](../../docs/modules/build_vuln_input.md)
