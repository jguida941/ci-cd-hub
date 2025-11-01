#!/usr/bin/env bash
# Test egress control per plan.md:32,85
# Production-ready approach for GitHub-hosted runners
#
# CURRENT STATE (GitHub-hosted):
#   - Validates connectivity to required destinations
#   - Documents egress allowlist for network policy enforcement
#   - Generates evidence for audit
#
# FUTURE STATE (Self-hosted with NetworkPolicy):
#   - Kubernetes NetworkPolicy or equivalent enforces default-deny
#   - This script validates enforcement by testing blocked destinations
#
# See docs/RUNNER_ISOLATION.md for network policy configuration

set -euo pipefail

REPORT_FILE="${1:-artifacts/security/egress-test.json}"
EVIDENCE_DIR="$(dirname "$REPORT_FILE")"
mkdir -p "$EVIDENCE_DIR"

log() {
  echo "[egress-test] $*" >&2
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "${EVIDENCE_DIR}/egress-test.log"
}

# Required destinations (allowlist for network policy)
# Format: "hostname:port:protocol:purpose"
declare -A REQUIRED_DESTINATIONS=(
  ["github.com:443:https"]="Source code, API"
  ["api.github.com:443:https"]="GitHub API"
  ["ghcr.io:443:https"]="Container registry"
  ["registry.npmjs.org:443:https"]="NPM packages"
  ["pypi.org:443:https"]="Python packages"
  ["files.pythonhosted.org:443:https"]="Python package files"
  ["rekor.sigstore.dev:443:https"]="Transparency log"
  ["fulcio.sigstore.dev:443:https"]="Certificate authority"
  ["tuf-repo-cdn.sigstore.dev:443:https"]="TUF repository"
  ["objects.githubusercontent.com:443:https"]="GitHub artifacts"
)

# Destinations that SHOULD be blocked (for testing enforcement)
# Only tested when EGRESS_ENFORCEMENT_MODE=strict
declare -A FORBIDDEN_DESTINATIONS=(
  ["example.com:443:https"]="Public test domain"
  ["httpbin.org:443:https"]="HTTP testing service"
)

ENFORCEMENT_MODE="${EGRESS_ENFORCEMENT_MODE:-audit}"
PASSED=0
FAILED=0
WARNINGS=0

test_connectivity() {
  local endpoint="$1"
  local host="${endpoint%%:*}"
  local rest="${endpoint#*:}"
  local port="${rest%%:*}"
  local purpose="${2:-unknown}"

  # Test TCP connectivity
  if timeout 5 bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
    log "✓ ${host}:${port} reachable - ${purpose}"
    PASSED=$((PASSED + 1))
    return 0
  else
    log "✗ ${host}:${port} NOT reachable - ${purpose}"
    FAILED=$((FAILED + 1))
    return 1
  fi
}

test_forbidden() {
  local endpoint="$1"
  local host="${endpoint%%:*}"
  local rest="${endpoint#*:}"
  local port="${rest%%:*}"
  local purpose="${2:-unknown}"

  # In audit mode, skip forbidden tests (can't block on GitHub-hosted)
  if [[ "$ENFORCEMENT_MODE" == "audit" ]]; then
    log "⊘ ${host}:${port} skipped in audit mode - ${purpose}"
    WARNINGS=$((WARNINGS + 1))
    return 0
  fi

  # Test that connection is blocked
  if timeout 5 bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
    log "✗ ${host}:${port} reachable (SHOULD BE BLOCKED) - ${purpose}"
    FAILED=$((FAILED + 1))
    return 1
  else
    log "✓ ${host}:${port} blocked as expected - ${purpose}"
    PASSED=$((PASSED + 1))
    return 0
  fi
}

generate_network_policy() {
  local policy_file="${EVIDENCE_DIR}/egress-allowlist.yaml"

  cat > "$policy_file" <<'EOF'
# Kubernetes NetworkPolicy for egress control
# Apply this to self-hosted runner namespace for enforcement
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ci-runner-egress-allowlist
  namespace: github-runners
spec:
  podSelector:
    matchLabels:
      app: github-runner
  policyTypes:
  - Egress
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
  # Allow required destinations
EOF

  for endpoint in "${!REQUIRED_DESTINATIONS[@]}"; do
    local host="${endpoint%%:*}"
    local rest="${endpoint#*:}"
    local port="${rest%%:*}"
    local purpose="${REQUIRED_DESTINATIONS[$endpoint]}"

    cat >> "$policy_file" <<EOF
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: ${port}
    # ${host} - ${purpose}
EOF
  done

  log "Generated NetworkPolicy template: ${policy_file}"
}

log "Starting egress control validation"
log "Mode: ${ENFORCEMENT_MODE}"
log "================================================"

# Test required destinations
log ""
log "Testing required destinations (allowlist)..."
for endpoint in "${!REQUIRED_DESTINATIONS[@]}"; do
  purpose="${REQUIRED_DESTINATIONS[$endpoint]}"
  test_connectivity "$endpoint" "$purpose" || true
done

# Test forbidden destinations (only in strict mode)
if [[ "$ENFORCEMENT_MODE" == "strict" ]]; then
  log ""
  log "Testing forbidden destinations (denylist)..."
  for endpoint in "${!FORBIDDEN_DESTINATIONS[@]}"; do
    purpose="${FORBIDDEN_DESTINATIONS[$endpoint]}"
    test_forbidden "$endpoint" "$purpose" || true
  done
else
  log ""
  log "Skipping denylist tests (enforcement_mode=${ENFORCEMENT_MODE})"
  log "Set EGRESS_ENFORCEMENT_MODE=strict to test blocking"
fi

# Generate network policy template
generate_network_policy

log ""
log "================================================"
log "Results: ${PASSED} passed, ${FAILED} failed, ${WARNINGS} warnings"

# Generate JSON report
cat > "$REPORT_FILE" <<EOF
{
  "enforcement_mode": "${ENFORCEMENT_MODE}",
  "runner_type": "${RUNNER_TYPE:-github-hosted}",
  "passed": ${PASSED},
  "failed": ${FAILED},
  "warnings": ${WARNINGS},
  "total": $((PASSED + FAILED + WARNINGS)),
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "$( [[ $FAILED -eq 0 ]] && echo "pass" || echo "fail" )",
  "required_destinations": $(printf '%s\n' "${!REQUIRED_DESTINATIONS[@]}" | jq -R . | jq -s .),
  "network_policy_template": "${EVIDENCE_DIR}/egress-allowlist.yaml"
}
EOF

if [[ $FAILED -gt 0 ]]; then
  log "ERROR: Egress control validation failed"
  log "Evidence: ${REPORT_FILE}"
  exit 1
else
  if [[ $WARNINGS -gt 0 ]]; then
    log "WARNING: Running in audit mode - enforcement not validated"
    log "Deploy network policies for full enforcement"
  fi
  log "SUCCESS: Egress control validation passed"
  log "Evidence: ${REPORT_FILE}"
  exit 0
fi
