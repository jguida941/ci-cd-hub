#!/bin/bash
set -euo pipefail

# Claude Code stop hook for the internal AI CI loop (Ralph Wiggum pattern).
# Set CIHUB_AI_LOOP=true to enable.

if [[ "${CIHUB_AI_LOOP:-}" != "true" ]]; then
  exit 0
fi

REPO="${CIHUB_REPO:-.}"
OUTPUT_DIR="${CIHUB_OUTPUT_DIR:-.cihub/ai-loop}"
MAX_ITERATIONS="${CIHUB_MAX_ITERATIONS:-10}"
FIX_MODE="${CIHUB_AI_LOOP_FIX_MODE:-safe}" # safe|report-only
EMIT_REPORT="${CIHUB_AI_LOOP_EMIT_REPORT:-false}"
REVIEW_CMD="${CIHUB_AI_REVIEW_CMD:-}"

mkdir -p "$OUTPUT_DIR"
export CIHUB_OUTPUT_DIR="$OUTPUT_DIR"

ITERATION_FILE="$OUTPUT_DIR/ai-loop-iteration"
ITERATION=0
if [[ -f "$ITERATION_FILE" ]]; then
  ITERATION=$(cat "$ITERATION_FILE" 2>/dev/null || echo 0)
fi
ITERATION=$((ITERATION + 1))
echo "$ITERATION" > "$ITERATION_FILE"
export CIHUB_AI_LOOP_ITERATION="$ITERATION"
export CIHUB_AI_LOOP_MAX_ITERATIONS="$MAX_ITERATIONS"
ITERATION_DIR="$OUTPUT_DIR/iteration-$ITERATION"
mkdir -p "$ITERATION_DIR"

CIHUB_EMIT_TRIAGE=true \
  python -m cihub ci --json --repo "$REPO" --output-dir "$ITERATION_DIR" \
  > "$ITERATION_DIR/ci-result.json" 2>/dev/null || true

EXIT_CODE=$(python - <<'PY'
import json
import os

path = os.path.join(os.environ.get("CIHUB_OUTPUT_DIR", ".cihub"), f"iteration-{os.environ.get('CIHUB_AI_LOOP_ITERATION','')}", "ci-result.json")
try:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    print(int(payload.get("exit_code", 1)))
except Exception:
    print(1)
PY
)

if [[ "$EXIT_CODE" == "0" ]]; then
  exit 0
fi

is_true() {
  case "$1" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if [[ "$FIX_MODE" == "safe" ]]; then
  python -m cihub fix --safe --repo "$REPO" >/dev/null 2>&1 || true
fi

if [[ "$FIX_MODE" == "report-only" ]] || is_true "$EMIT_REPORT"; then
  python -m cihub fix --report --ai --repo "$REPO" >/dev/null 2>&1 || true
fi

if [[ -n "$REVIEW_CMD" ]]; then
  /bin/sh -c "$REVIEW_CMD" > "$ITERATION_DIR/review.md" 2>&1 || true
fi

if [[ "$ITERATION" -ge "$MAX_ITERATIONS" ]]; then
  exit 1
fi

# Exit 2 tells Claude Code to continue (hook convention).
exit 2
