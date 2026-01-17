"""Secrets command handlers."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.repo_config import get_connected_repos
from cihub.types import CommandResult
from cihub.utils import resolve_executable
from cihub.utils.exec_utils import (
    TIMEOUT_NETWORK,
    CommandNotFoundError,
    CommandTimeoutError,
    safe_run,
)
from cihub.utils.net import safe_urlopen


def _verify_token(pat: str) -> tuple[bool, str]:
    """Verify GitHub PAT by making a test API request."""
    req = urllib.request.Request(  # noqa: S310
        "https://api.github.com/user",
        headers={
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "cihub",
        },
    )
    try:
        with safe_urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scopes = resp.headers.get("X-OAuth-Scopes", "")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return False, "unauthorized (token invalid or expired)"
        return False, f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:
        return False, str(exc)

    login = data.get("login", "unknown")
    scope_msg = f"scopes: {scopes}" if scopes else "scopes: (not reported)"
    return True, f"user {login} ({scope_msg})"


def _verify_cross_repo_access(pat: str, target_repo: str) -> tuple[bool, str]:
    """Verify token can access another repo's artifacts."""
    req = urllib.request.Request(  # noqa: S310
        f"https://api.github.com/repos/{target_repo}/actions/artifacts",
        headers={
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "cihub",
        },
    )
    try:
        with safe_urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            count = data.get("total_count", 0)
            return True, f"{count} artifacts accessible"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False, f"repo not found or no access: {target_repo}"
        if exc.code == 401:
            return False, "token cannot access this repo (needs 'repo' scope)"
        return False, f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:
        return False, str(exc)


def _verify_nvd_key(key: str) -> tuple[bool, str]:
    """Verify NVD API key by making a test request."""
    test_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228"
    req = urllib.request.Request(  # noqa: S310
        test_url,
        headers={
            "apiKey": key,
            "User-Agent": "cihub",
        },
    )
    try:
        with safe_urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return True, "NVD API key is valid"
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            return False, "invalid or expired API key"
        if exc.code == 404:
            return True, "API key accepted (test CVE not found)"
        return False, f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:
        return False, str(exc)
    return True, "API key accepted"


def _set_secret(gh_bin: str, repo: str, secret_name: str, secret_value: str) -> tuple[bool, str]:
    """Set a GitHub Actions secret on a repo."""
    try:
        result = safe_run(
            [gh_bin, "secret", "set", secret_name, "-R", repo],
            input=secret_value,
            timeout=TIMEOUT_NETWORK,
        )
    except CommandNotFoundError:
        return False, "gh not found"
    except CommandTimeoutError:
        return False, "timed out setting secret"
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


def cmd_setup_secrets(args: argparse.Namespace) -> CommandResult:
    """Set HUB_DISPATCH_TOKEN on hub and optionally all connected repos."""
    import getpass

    hub_repo = args.hub_repo or os.environ.get("CIHUB_HUB_REPO", "")
    token = args.token
    json_mode = getattr(args, "json", False)

    if not hub_repo:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Hub repo is required (set --hub-repo or CIHUB_HUB_REPO)",
            problems=[
                {
                    "severity": "error",
                    "message": "Hub repo is required (set --hub-repo or CIHUB_HUB_REPO)",
                    "code": "CIHUB-SECRETS-NO-HUB-REPO",
                }
            ],
        )

    # Non-interactive mode requires --token
    if json_mode and not token:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Non-interactive mode requires --token",
            problems=[
                {
                    "severity": "error",
                    "message": "Non-interactive mode requires --token",
                    "code": "CIHUB-SECRETS-REQUIRES-TOKEN",
                }
            ],
        )

    # Token prompt (interactive only)
    if not token:
        token = getpass.getpass("Enter GitHub PAT: ")

    token = token.strip()

    if not token:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No token provided",
            problems=[
                {
                    "severity": "error",
                    "message": "No token provided",
                    "code": "CIHUB-SECRETS-NO-TOKEN",
                }
            ],
        )

    if any(ch.isspace() for ch in token):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Token contains whitespace; paste the raw token value",
            problems=[
                {
                    "severity": "error",
                    "message": "Token contains whitespace; paste the raw token value",
                    "code": "CIHUB-SECRETS-INVALID-TOKEN",
                }
            ],
        )

    messages: list[str] = []
    problems: list[dict[str, Any]] = []

    # Verification step
    if args.verify:
        ok, message = _verify_token(token)
        if not ok:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Token verification failed: {message}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"Token verification failed: {message}",
                        "code": "CIHUB-SECRETS-VERIFY-FAILED",
                    }
                ],
            )
        messages.append(f"Token verified: {message}")

        connected = get_connected_repos()
        if connected:
            test_repo = connected[0]
            ok, message = _verify_cross_repo_access(token, test_repo)
            if not ok:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary=f"Cross-repo access failed for {test_repo}: {message}",
                    problems=[
                        {
                            "severity": "error",
                            "message": f"Cross-repo access failed for {test_repo}: {message}",
                            "code": "CIHUB-SECRETS-CROSS-REPO-FAILED",
                        },
                        {
                            "severity": "info",
                            "message": "The token needs 'repo' scope to access other repos' artifacts",
                            "code": "CIHUB-SECRETS-SCOPE-HINT",
                        },
                    ],
                )
            messages.append(f"Cross-repo access verified: {test_repo} ({message})")

    gh_bin = resolve_executable("gh")

    # Set secret on hub repo
    messages.append(f"Setting HUB_DISPATCH_TOKEN on {hub_repo}...")
    ok, error = _set_secret(gh_bin, hub_repo, "HUB_DISPATCH_TOKEN", token)
    if not ok:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"Failed to set secret on {hub_repo}: {error}",
            problems=[
                {
                    "severity": "error",
                    "message": f"Failed to set secret on {hub_repo}: {error}",
                    "code": "CIHUB-SECRETS-SET-FAILED",
                }
            ],
        )
    messages.append(f"[OK] {hub_repo}")

    # Set on connected repos if --all
    repo_results: list[dict[str, str]] = []
    failures = 0
    if args.all:
        messages.append("Setting on connected repos...")
        repos = get_connected_repos()
        for repo in repos:
            if repo == hub_repo:
                continue
            ok, error = _set_secret(gh_bin, repo, "HUB_DISPATCH_TOKEN", token)
            if ok:
                messages.append(f"[OK] {repo}")
                repo_results.append({"repo": repo, "status": "updated"})
            else:
                suffix = f" ({error})" if error else " (no admin access)"
                messages.append(f"[FAIL] {repo}{suffix}")
                repo_results.append({"repo": repo, "status": "failed", "message": error or ""})
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Failed to set secret on {repo}: {error or 'no admin access'}",
                        "code": "CIHUB-SECRETS-REPO-FAILED",
                    }
                )
                failures += 1

    # Build summary
    connected_repos = get_connected_repos()
    suggestions = []
    if connected_repos:
        suggestions.append(
            {"message": "Ensure PAT has 'repo' scope (classic) or Actions R/W (fine-grained) on all repos"}
        )

    summary = "Secrets updated" if failures == 0 else f"Secrets updated with {failures} failure(s)"

    return CommandResult(
        exit_code=EXIT_FAILURE if failures else EXIT_SUCCESS,
        summary=summary,
        problems=problems,
        suggestions=suggestions,
        data={
            "hub_repo": hub_repo,
            "repos": repo_results,
            "connected_repos": connected_repos,
            "items": messages,
        },
    )


def cmd_setup_nvd(args: argparse.Namespace) -> CommandResult:
    """Set NVD_API_KEY on Java repos for OWASP Dependency Check."""
    import getpass

    nvd_key = args.nvd_key
    json_mode = getattr(args, "json", False)

    # Non-interactive mode requires --nvd-key
    if json_mode and not nvd_key:
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary="Non-interactive mode requires --nvd-key",
            problems=[
                {
                    "severity": "error",
                    "message": "Non-interactive mode requires --nvd-key",
                    "code": "CIHUB-NVD-REQUIRES-KEY",
                }
            ],
            suggestions=[{"message": "Get a free key at: https://nvd.nist.gov/developers/request-an-api-key"}],
        )

    # Key prompt (interactive only)
    if not nvd_key:
        nvd_key = getpass.getpass("Enter NVD API Key: ")

    nvd_key = nvd_key.strip()

    if not nvd_key:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="No NVD API key provided",
            problems=[
                {
                    "severity": "error",
                    "message": "No NVD API key provided",
                    "code": "CIHUB-NVD-NO-KEY",
                }
            ],
            suggestions=[{"message": "Get a free key at: https://nvd.nist.gov/developers/request-an-api-key"}],
        )

    if any(ch.isspace() for ch in nvd_key):
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary="Key contains whitespace; paste the raw key value",
            problems=[
                {
                    "severity": "error",
                    "message": "Key contains whitespace; paste the raw key value",
                    "code": "CIHUB-NVD-INVALID-KEY",
                }
            ],
        )

    messages: list[str] = []
    problems: list[dict[str, Any]] = []

    # Verification step
    if args.verify:
        messages.append("Verifying NVD API key...")
        ok, message = _verify_nvd_key(nvd_key)
        if not ok:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"NVD API key verification failed: {message}",
                problems=[
                    {
                        "severity": "error",
                        "message": f"NVD API key verification failed: {message}",
                        "code": "CIHUB-NVD-VERIFY-FAILED",
                    }
                ],
            )
        messages.append(f"NVD API key verified: {message}")

    gh_bin = resolve_executable("gh")

    java_repos = get_connected_repos(
        only_dispatch_enabled=False,
        language_filter="java",
    )

    if not java_repos:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="No Java repos found",
            data={
                "repos": [],
                "items": [
                    "No Java repos found in config/repos/*.yaml",
                    "NVD_API_KEY is only needed for Java repos (OWASP Dependency Check)",
                ],
            },
        )

    messages.append(f"Setting NVD_API_KEY on {len(java_repos)} Java repo(s)...")
    success_count = 0
    repo_results: list[dict[str, str]] = []

    for repo in java_repos:
        ok, error = _set_secret(gh_bin, repo, "NVD_API_KEY", nvd_key)
        if ok:
            messages.append(f"[OK] {repo}")
            success_count += 1
            repo_results.append({"repo": repo, "status": "updated"})
        else:
            suffix = f" ({error})" if error else " (no admin access)"
            messages.append(f"[FAIL] {repo}{suffix}")
            repo_results.append({"repo": repo, "status": "failed", "message": error or ""})
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Failed to set secret on {repo}: {error or 'no admin access'}",
                    "code": "CIHUB-NVD-REPO-FAILED",
                }
            )

    failures = len(java_repos) - success_count
    summary = f"NVD key set on {success_count}/{len(java_repos)} Java repos"

    suggestions = []
    if failures > 0:
        suggestions.append(
            {
                "message": (
                    "For repos you don't have admin access to, "
                    "set the secret manually: gh secret set NVD_API_KEY -R owner/repo"
                )
            }
        )

    return CommandResult(
        exit_code=EXIT_FAILURE if failures else EXIT_SUCCESS,
        summary=summary,
        problems=problems,
        suggestions=suggestions,
        data={
            "repos": repo_results,
            "success_count": success_count,
            "total_count": len(java_repos),
            "items": messages,
        },
    )
