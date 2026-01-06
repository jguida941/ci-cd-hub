"""CI service entrypoint for GUI/programmatic access."""

from __future__ import annotations

from cihub.services.ci_engine import CiRunResult, RunCIOptions, run_ci

__all__ = ["CiRunResult", "RunCIOptions", "run_ci"]
