"""CI service entrypoint for GUI/programmatic access."""

from __future__ import annotations

from cihub.services.ci_engine import CiRunResult, run_ci

__all__ = ["CiRunResult", "run_ci"]
