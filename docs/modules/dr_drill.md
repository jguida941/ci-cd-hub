# DR Drill Simulator

## Purpose
Exercise a lightweight disaster-recovery scenario and capture JSON + NDJSON evidence for compliance audits.

## Usage
```bash
python tools/run_dr_drill.py \
  --output artifacts/evidence/dr/dr-report.json \
  --ndjson artifacts/evidence/dr/dr-events.ndjson
```

## Drill Steps
The simulator currently runs three sequential stages:
1. `snapshot_backup` – capture the production snapshot metadata.
2. `restore_to_staging` – simulate restoration into a staging cluster.
3. `verify_integrity` – smoke-test the restored services.

Each step emits start/end timestamps, a `status`, and notes that describe the action taken.

## Outputs
- JSON summary (`schema=dr_drill.v1`) with the full ordered event list.
- NDJSON stream with the same `DrillEvent` entries for data lake ingestion.

## Dependencies
- Python 3.12+
- Standard library only.

## Workflows
`.github/workflows/dr-drill.yml` orchestrates weekly runs and uploads the evidence artifact.

## License
See [LICENSE](../../LICENSE).

**Back to:** [Overview](../OVERVIEW.md)
