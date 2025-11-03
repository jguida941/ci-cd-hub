#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARGS=("$@")

cd "$REPO_ROOT"

if [[ "${SKIP_MARKDOWNLINT:-}" == "1" ]]; then
  echo "[markdownlint] SKIP_MARKDOWNLINT=1 set; skipping markdown lint." >&2
  exit 0
fi

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    exec docker run --rm -v "${REPO_ROOT}:/workdir" davidanson/markdownlint-cli2:v0.18.1 "${ARGS[@]}"
  else
    echo "[markdownlint] Docker CLI found but daemon not reachable; falling back to npx." >&2
  fi
fi

if command -v npx >/dev/null 2>&1; then
  exec npx --yes markdownlint-cli2@0.18.1 "${ARGS[@]}"
fi

echo "[markdownlint] docker and npx are unavailable. Install Docker Desktop or Node.js (npm) to run markdownlint." >&2
exit 1
