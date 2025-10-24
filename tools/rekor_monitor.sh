#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  >&2 echo "Usage: $0 <image-digest> <subject> <output-dir>"
  exit 1
fi

DIGEST="$1"
SUBJECT="$2"
OUTPUT_DIR="$3"
mkdir -p "$OUTPUT_DIR"

REKOR_LOG=${REKOR_LOG:-https://rekor.sigstore.dev}

if ! command -v rekor-cli >/dev/null 2>&1; then
  >&2 echo "rekor-cli not found; install via https://github.com/sigstore/rekor"
  exit 1
fi

HAS_LOG_URL=1
if ! rekor-cli search --help 2>&1 | grep -q -- "--log-url"; then
  HAS_LOG_URL=0
fi

TIMESTAMP=$(date -u '+%Y%m%dT%H%M%SZ')
PROOF_PATH="$OUTPUT_DIR/rekor-proof-${TIMESTAMP}.json"
SEARCH_PATH="$OUTPUT_DIR/rekor-search-${TIMESTAMP}.json"

if [[ "$HAS_LOG_URL" -eq 1 ]]; then
  rekor-cli search --sha "$DIGEST" --log-url "$REKOR_LOG" --format json > "$SEARCH_PATH"
else
  rekor-cli --rekor_server "$REKOR_LOG" search --sha "$DIGEST" --format json > "$SEARCH_PATH"
fi

UUID=$(jq -r '
  if type == "array" then
    (.[0].uuid // empty)
  elif type == "object" then
    (.uuid // empty)
  else
    empty
  end
' "$SEARCH_PATH")

if [[ -z "$UUID" ]]; then
  >&2 echo "[rekor_monitor] No Rekor entries found for digest $DIGEST"
  exit 1
fi

if [[ "$HAS_LOG_URL" -eq 1 ]]; then
  rekor-cli verify --uuid "$UUID" --log-url "$REKOR_LOG" --format json > "$PROOF_PATH"
else
  rekor-cli --rekor_server "$REKOR_LOG" verify --uuid "$UUID" --format json > "$PROOF_PATH"
fi

echo "Stored Rekor inclusion proof at $PROOF_PATH"

jq -n \
  --arg subject "$SUBJECT" \
  --arg digest "$DIGEST" \
  --arg proof_path "$PROOF_PATH" \
  --arg timestamp "$TIMESTAMP" \
  '{"subject":$subject,"digest":$digest,"proof_path":$proof_path,"timestamp":$timestamp}' \
  > "$OUTPUT_DIR/rekor-proof-index-${TIMESTAMP}.json"
