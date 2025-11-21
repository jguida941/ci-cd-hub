# Generate VEX

## Purpose
Convert `fixtures/supply_chain/vex_exemptions.json` into a CycloneDX VEX document for the current release artifact.

## Usage
```bash
python tools/generate_vex.py \
  --config fixtures/supply_chain/vex_exemptions.json \
  --output artifacts/sbom/app.vex.json \
  --subject ghcr.io/org/image@sha256:<digest> \
  --manufacturer <org> \
  --product <image-name>
```

## Configuration
- Input config: exemption statements (ID, status, justification, impact, source).
- Output schema: `schema/cyclonedx-vex-1.5.schema.json`.

## Testing
```bash
pytest tools/tests/test_generate_vex.py
```

## Dependencies
- Python 3.12+
- `jsonschema`

## Output & Artifacts
- CycloneDX VEX: `artifacts/sbom/app.vex.json`

**Back to:** [Overview](../../docs/OVERVIEW.md) · [Testing](../../docs/TESTING.md) · [Module doc](../../docs/modules/generate_vex.md)
