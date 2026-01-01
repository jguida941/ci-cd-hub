#!/bin/bash
# =============================================================================
# DEPRECATED: This script is a shim for backwards compatibility.
#
# Use: cihub report validate --report <path> [OPTIONS]
#
# This shim will be removed in the next release.
# =============================================================================

set -euo pipefail

echo "[DEPRECATED] scripts/validate_report.sh: use 'cihub report validate' instead" >&2

# Parse args and translate to new CLI format
REPORT=""
STACK=""
EXPECT="clean"
COVERAGE_MIN="70"
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --report)
            REPORT="$2"
            shift 2
            ;;
        --stack)
            STACK="$2"
            shift 2
            ;;
        --expect-clean)
            EXPECT="clean"
            shift
            ;;
        --expect-issues)
            EXPECT="issues"
            shift
            ;;
        --coverage-min)
            COVERAGE_MIN="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --help|-h)
            echo "DEPRECATED: Use 'cihub report validate --help' instead"
            python -m cihub report validate --help
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$REPORT" ]]; then
    echo "Error: --report is required" >&2
    exit 1
fi

# Note: --stack is no longer needed; the CLI auto-detects from report.json
# shellcheck disable=SC2086
python -m cihub report validate \
    --report "$REPORT" \
    --expect "$EXPECT" \
    --coverage-min "$COVERAGE_MIN" \
    $VERBOSE
