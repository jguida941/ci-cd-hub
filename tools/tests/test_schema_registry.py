from __future__ import annotations

import json
from subprocess import CompletedProcess
import sys
from pathlib import Path

from tools.safe_subprocess import run_checked

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_registry_check(registry: Path) -> CompletedProcess[str]:
    cmd = [sys.executable, "scripts/check_schema_registry.py", "--registry", str(registry)]
    # Safe: invokes repository validation script with controlled arguments.
    return run_checked(
        cmd,
        allowed_programs={sys.executable},
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_registry_validation_succeeds():
    registry_path = REPO_ROOT / "schema" / "registry.json"
    result = _run_registry_check(registry_path)
    assert result.returncode == 0, result.stderr


def test_registry_validation_detects_missing_fixture(tmp_path: Path):
    registry_path = REPO_ROOT / "schema" / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    topic = registry["topics"]["pipeline_run"]
    schema_version = topic["schema_versions"][0]
    schema_version["path"] = str((REPO_ROOT / schema_version["path"]).resolve())
    schema_version["fixtures"] = [
        str((REPO_ROOT / "fixtures" / "pipeline_run_v1_2" / "missing.ndjson").resolve())
    ]
    ingestion = topic.get("ingestion", {})
    if "warehouse_model" in ingestion:
        ingestion["warehouse_model"] = str((REPO_ROOT / ingestion["warehouse_model"]).resolve())
    if "dbt_models" in ingestion:
        ingestion["dbt_models"] = [str((REPO_ROOT / model).resolve()) for model in ingestion["dbt_models"]]
    broken_registry = tmp_path / "registry.json"
    broken_registry.write_text(json.dumps(registry), encoding="utf-8")

    result = _run_registry_check(broken_registry)
    assert result.returncode != 0
    stderr = result.stderr
    assert "missing fixture" in stderr.lower()
