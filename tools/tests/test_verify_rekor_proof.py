from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.verify_rekor_proof import load_index, verify_proof

FIXTURE_DIR = Path(__file__).resolve().parents[0] / "fixtures" / "rekor"


def _prepare(tmp_path: Path) -> tuple[Path, Path]:
    proof = tmp_path / "proof.json"
    proof.write_text((FIXTURE_DIR / "proof.json").read_text(), encoding="utf-8")
    index = tmp_path / "rekor-proof-index-20250101T000000Z.json"
    index.write_text((FIXTURE_DIR / "index.json").read_text(), encoding="utf-8")
    return proof, index


def test_verify_rekor_proof_success(tmp_path: Path) -> None:
    proof_path, index_path = _prepare(tmp_path)
    index = load_index(index_path)
    assert index["proof_path"] == "proof.json"
    verify_proof(proof_path, index["digest"])


def test_verify_rekor_proof_digest_mismatch(tmp_path: Path) -> None:
    proof_path, index_path = _prepare(tmp_path)
    with pytest.raises(SystemExit, match="expected digest not present"):
        verify_proof(proof_path, "sha256:0000000000000000000000000000000000000000000000000000000000000000")


def test_verify_rekor_proof_missing_inclusion(tmp_path: Path) -> None:
    proof_path, index_path = _prepare(tmp_path)
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["verification"].pop("inclusionProof", None)
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    with pytest.raises(SystemExit, match="inclusion proof missing"):
        verify_proof(proof_path, load_index(index_path)["digest"])


def test_verify_rekor_proof_legacy_structure(tmp_path: Path) -> None:
    proof_path, index_path = _prepare(tmp_path)
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    legacy = {"Entry": proof["logEntry"], "Verification": proof["verification"]}
    proof_path.write_text(json.dumps(legacy), encoding="utf-8")
    verify_proof(proof_path, load_index(index_path)["digest"])


def test_verify_rekor_proof_list_wrapper(tmp_path: Path) -> None:
    proof_path, index_path = _prepare(tmp_path)
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof_path.write_text(json.dumps([proof]), encoding="utf-8")
    verify_proof(proof_path, load_index(index_path)["digest"])
