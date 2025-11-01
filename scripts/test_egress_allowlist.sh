i#!/usr/bin/env bash
# Test default-deny egress control per plan.md:32,85
# Ensures only approved destinations are reachable

set -euo pipefail

log() {
  echo "[egress-test] $*" >&2
}

# Approved destinations (allowlist)
ALLOWED_HOSTS=(
  "github.com"
  "api.github.com"
  "ghcr.io"
  "registry.npmjs.org"
  "pypi.org"
  "files.pythonhosted.org"
  "rekor.sigstore.dev"
  "fulcio.sigstore.dev"
  "tuf-repo-cdn.sigstore.dev"
  "objects.githubusercontent.com"
)

# Forbidden destinations (should be blocked)
FORBIDDEN_HOSTS=(
  "example.com"
  "evil.example.net"
  "attacker-c2.example.org"
)

PASSED=0
FAILED=0

test_allowed() {
  local host="$1"
  log "Testing allowed host: $host"

  if timeout 5 curl -fsSL -I "https://${host}" -o /dev/null 2>&1; then
    log "✓ ${host} is reachable (expected)"
    PASSED=$((PASSED + 1))
    return 0
  else
    log "✗ ${host} is NOT reachable (UNEXPECTED - should be allowed)"
    FAILED=$((FAILED + 1))
    return 1
  fi
}

test_forbidden() {
  local host="$1"
  log "Testing forbidden host: $host"

  if timeout 5 curl -fsSL -I "https://${host}" -o /dev/null 2>&1; then
    log "✗ ${host} is reachable (UNEXPECTED - should be blocked)"
    FAILED=$((FAILED + 1))
    return 1
  else
    log "✓ ${host} is NOT reachable (expected - blocked by egress control)"
    PASSED=$((PASSED + 1))
    return 0
  fi
}

log "Starting egress allowlist smoke test"
log "================================================"

# Test allowed hosts
log "Testing allowlist (should all be reachable)..."
for host in "${ALLOWED_HOSTS[@]}"; do
  test_allowed "$host" || true
done

log ""
log "Testing denylist (should all be blocked)..."
for host in "${FORBIDDEN_HOSTS[@]}"; do
  test_forbidden "$host" || true
done

log ""
log "================================================"
log "Results: ${PASSED} passed, ${FAILED} failed"

if [[ $FAILED -gt 0 ]]; then
  log "ERROR: Egress control test failed"
  log "Expected behavior:"
  log "  - Allowed hosts should be reachable"
  log "  - Forbidden hosts should be blocked"
  exit 1
else
  log "SUCCESS: All egress control tests passed"
  exit 0
fi