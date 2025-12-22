#!/usr/bin/env bash
# =============================================================================
# Setup Secrets Script
# =============================================================================
# Pushes HUB_DISPATCH_TOKEN to the hub repo and optionally to all connected repos.
#
# Usage:
#   ./scripts/setup-secrets.sh                    # Interactive - prompts for token
#   ./scripts/setup-secrets.sh --token <PAT>      # Non-interactive
#   ./scripts/setup-secrets.sh --all              # Also push to all connected repos
#
# Requirements:
#   - gh CLI authenticated
#   - PAT with repo + workflow scopes (classic) or Actions R/W (fine-grained)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUB_ROOT="$(dirname "$SCRIPT_DIR")"
HUB_REPO="jguida941/ci-cd-hub"

# Parse args
TOKEN=""
PUSH_ALL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --token)
      TOKEN="$2"
      shift 2
      ;;
    --all)
      PUSH_ALL=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Get token interactively if not provided
if [[ -z "$TOKEN" ]]; then
  echo "Enter your GitHub PAT (will not echo):"
  read -rs TOKEN
  echo ""
fi

if [[ -z "$TOKEN" ]]; then
  echo "Error: No token provided"
  exit 1
fi

# Get unique repos from config
get_repos() {
  python3 - "$HUB_ROOT" <<'PY'
import sys
from pathlib import Path
import yaml

hub_root = Path(sys.argv[1])
repos_dir = hub_root / "config" / "repos"

seen = set()
for cfg_file in repos_dir.glob("*.yaml"):
    if cfg_file.name.endswith(".disabled"):
        continue
    try:
        data = yaml.safe_load(cfg_file.read_text()) or {}
        repo = data.get("repo", {})
        owner = repo.get("owner", "")
        name = repo.get("name", "")
        if owner and name:
            full = f"{owner}/{name}"
            if full not in seen:
                seen.add(full)
                print(full)
    except Exception:
        pass
PY
}

echo "=== Setting HUB_DISPATCH_TOKEN on hub repo ==="
echo "$TOKEN" | gh secret set HUB_DISPATCH_TOKEN -R "$HUB_REPO" --body -
echo "✅ Set on $HUB_REPO"

if $PUSH_ALL; then
  echo ""
  echo "=== Setting HUB_DISPATCH_TOKEN on connected repos ==="

  for repo in $(get_repos); do
    if [[ "$repo" == "$HUB_REPO" ]]; then
      continue
    fi
    echo -n "Setting on $repo... "
    if echo "$TOKEN" | gh secret set HUB_DISPATCH_TOKEN -R "$repo" --body - 2>/dev/null; then
      echo "✅"
    else
      echo "❌ (no admin access or repo doesn't exist)"
    fi
  done
fi

echo ""
echo "=== Done ==="
echo ""
echo "Connected repos that need artifact access:"
for repo in $(get_repos); do
  echo "  - $repo"
done
echo ""
echo "Make sure your PAT has 'repo' scope (classic) or Actions R/W on all repos (fine-grained)."
