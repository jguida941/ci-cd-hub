# Mutation Observatory

## Purpose
Run mutation analyzers (Stryker, mutmut) and emit structured resilience telemetry for CI gating.

## Usage
```bash
python tools/mutation_observatory.py \
  --config config/mutation-observatory.ci.yaml \
  --output artifacts/mutation/run.json \
  --ndjson artifacts/mutation/run.ndjson \
  --markdown artifacts/mutation/summary.md
```

## Configuration
- `config/mutation-observatory.ci.yaml` defines targets (tool, parser, report path, thresholds).
- Optional commands can generate reports relative to `workdir`.

## Testing
```bash
pytest tools/tests/test_mutation_observatory.py
```

## Dependencies
- Python 3.12+
- Mutator backends per config when running full pipelines.

## Output & Artifacts
- JSON: `artifacts/mutation/run.json`
- NDJSON: `artifacts/mutation/run.ndjson`
- Markdown summary: `artifacts/mutation/summary.md`

**Back to:** [Overview](../../docs/OVERVIEW.md) · [Testing](../../docs/TESTING.md) · [Module doc](../../docs/modules/mutation_observatory.md)
