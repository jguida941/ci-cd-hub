"""Docker tool runner."""

from __future__ import annotations

import time
import urllib.request
from pathlib import Path

import yaml

from . import shared
from .base import ToolResult

# Health check polling configuration
HEALTH_CHECK_INTERVAL_SECONDS = 5
HEALTH_CHECK_HTTP_TIMEOUT_SECONDS = 5


def _resolve_docker_compose_command() -> list[str]:
    try:
        docker_bin = shared.resolve_executable("docker")
        return [docker_bin, "compose"]
    except FileNotFoundError:
        docker_compose = shared.resolve_executable("docker-compose")
        return [docker_compose]


def _parse_compose_port(value: object) -> int | None:
    if isinstance(value, dict):
        published = value.get("published")
        if isinstance(published, int):
            return published
        if isinstance(published, str) and published.isdigit():
            return int(published)
        return None
    if isinstance(value, str):
        base = value.split("/")[0]
        parts = base.split(":")
        if len(parts) < 2:
            return None
        host = parts[-2]
        if host.isdigit():
            return int(host)
    return None


def _parse_compose_ports(compose_path: Path) -> list[int]:
    try:
        data = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    services = data.get("services")
    if not isinstance(services, dict):
        return []
    ports: list[int] = []
    for service in services.values():
        if not isinstance(service, dict):
            continue
        for port in service.get("ports", []) or []:
            host_port = _parse_compose_port(port)
            if host_port is not None:
                ports.append(host_port)
    return ports


def _wait_for_health(ports: list[int], endpoint: str, timeout_seconds: int) -> bool:
    if not ports:
        return False
    deadline = time.monotonic() + max(timeout_seconds, 0)
    while time.monotonic() < deadline:
        for port in ports:
            url = f"http://localhost:{port}{endpoint}"
            try:
                with urllib.request.urlopen(url, timeout=HEALTH_CHECK_HTTP_TIMEOUT_SECONDS) as resp:  # noqa: S310
                    if 200 <= resp.status < 400:
                        return True
            except Exception:  # noqa: S112 - expected failures during health poll
                continue
        time.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
    return False


def run_docker(
    workdir: Path,
    output_dir: Path,
    compose_file: str = "docker-compose.yml",
    health_endpoint: str | None = None,
    health_timeout: int = 300,
) -> ToolResult:
    compose_path = workdir / compose_file
    if not compose_path.exists():
        return ToolResult(
            tool="docker",
            ran=False,
            success=False,
            metrics={"docker_missing_compose": True},
        )

    compose_cmd = _resolve_docker_compose_command()
    compose_args = [*compose_cmd, "-f", str(compose_path)]
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "docker-compose.log"
    proc_up = shared._run_tool_command("docker", [*compose_args, "up", "-d"], workdir, output_dir)
    ran = True
    success = proc_up.returncode == 0
    health_ok = None

    if success and health_endpoint:
        endpoint = health_endpoint.strip()
        if endpoint and not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        ports = _parse_compose_ports(compose_path)
        health_ok = _wait_for_health(ports, endpoint, int(health_timeout))
        success = success and health_ok

    proc_logs = shared._run_tool_command("docker", [*compose_args, "logs", "--no-color"], workdir, output_dir)
    log_contents = f"{proc_logs.stdout or ''}{proc_logs.stderr or ''}"
    if log_contents:
        log_path.write_text(log_contents, encoding="utf-8")

    shared._run_tool_command("docker", [*compose_args, "down", "--remove-orphans"], workdir, output_dir)

    metrics: dict[str, object] = {"docker_missing_compose": False}
    if health_endpoint:
        metrics["docker_health_ok"] = bool(health_ok)
    return ToolResult(
        tool="docker",
        ran=ran,
        success=success,
        metrics=metrics,
        artifacts={"log": str(log_path)} if log_path.exists() else {},
        stdout=proc_up.stdout,
        stderr=proc_up.stderr,
    )
