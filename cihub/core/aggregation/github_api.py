"""GitHub API helpers for aggregation."""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib import request


def _safe_extractall(zip_path: Path, target_dir: Path) -> None:
    """Extract ZIP with path traversal protection.

    Validates all members are within target_dir before extraction
    to prevent CVE-style path traversal attacks via malicious ZIPs.
    """
    target_dir = target_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            member_path = (target_dir / member).resolve()
            try:
                member_path.relative_to(target_dir)
            except ValueError:
                raise ValueError(f"Path traversal detected in ZIP: {member}") from None
        zf.extractall(target_dir)


class GitHubAPI:
    """GitHub API client with retry logic."""

    def __init__(self, token: str):
        self.token = token

    def get(self, url: str, retries: int = 3, backoff: float = 2.0, timeout: int = 30) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                req = request.Request(  # noqa: S310
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                    data = json.loads(resp.read().decode())
                    return data if isinstance(data, dict) else {}
            except Exception as exc:
                attempt += 1
                if attempt > retries:
                    raise
                sleep_for = backoff * attempt
                print(f"Retry {attempt}/{retries} for {url}: {exc} (sleep {sleep_for}s)")
                time.sleep(sleep_for)

    def download_artifact(self, archive_url: str, target_dir: Path) -> Path | None:
        """Download an artifact from GitHub.

        GitHub's artifact download API returns a 302 redirect to Azure Blob Storage.
        We must NOT send the Authorization header to Azure (it causes 401 errors).
        Instead, we manually handle the redirect: first get the redirect URL with auth,
        then download from Azure without auth.
        """
        print("   Downloading artifact...")

        # Step 1: Request the artifact URL with auth to get the redirect location
        # We use a custom opener that does NOT follow redirects automatically
        class NoRedirectHandler(request.HTTPRedirectHandler):
            def redirect_request(
                self,
                req: request.Request,
                fp: Any,
                code: int,
                msg: str,
                headers: Any,
                newurl: str,
            ) -> None:
                return None  # Don't follow redirects

        opener = request.build_opener(NoRedirectHandler)

        req = request.Request(  # noqa: S310
            archive_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            opener.open(req, timeout=60)  # noqa: S310
            # If we get here without redirect, something is wrong
            print("   WARNING: No redirect received from GitHub API")
            return None
        except request.HTTPError as e:
            if e.code == 302:
                # This is expected - GitHub redirects to Azure Blob Storage
                redirect_url = e.headers.get("Location")
                if not redirect_url:
                    print("   WARNING: 302 redirect but no Location header")
                    return None
            else:
                print(f"   Failed to get artifact redirect: HTTP {e.code}")
                return None
        except Exception as exc:
            print(f"   Failed to get artifact redirect: {exc}")
            return None

        # Step 2: Download from Azure Blob Storage WITHOUT auth headers
        try:
            req_azure = request.Request(redirect_url)  # noqa: S310
            with request.urlopen(req_azure, timeout=120) as resp:  # noqa: S310
                data = resp.read()
            target_dir.mkdir(parents=True, exist_ok=True)
            zip_path = target_dir / "artifact.zip"
            zip_path.write_bytes(data)
            _safe_extractall(zip_path, target_dir)
            print(f"   Artifact extracted to {target_dir}")
            return target_dir
        except Exception as exc:
            print(f"   Failed to download artifact from storage: {exc}")
            return None
