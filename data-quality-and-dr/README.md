# Data Quality & Disaster Recovery Assets

- `dr_recall.sh`: recovery helper that replays a DR bundle (backup + provenance + SBOM) into an output directory, emits a `recall.log`, restores the backup, and writes a SHA256 checksum. Use it for quarterly recall drills and keep the outputs under `artifacts/dr/restore/`.
- `models/tests/data_quality.yml`: dbt test definitions covering freshness, rowcount, and null-rate thresholds.
- WORM + replication policies are documented in `docs/DR_RUNBOOK.md`; keep this README in sync with that runbook.
