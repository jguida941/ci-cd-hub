# Claude Code Hooks (Internal)

These templates support the internal AI CI loop. They are not part of the public
CLI surface and are intended for internal use only.

## Installation

1. Copy `templates/hooks/stop.sh` to `~/.claude/hooks/stop.sh`
2. `chmod +x ~/.claude/hooks/stop.sh`

## Environment

- `CIHUB_AI_LOOP=true` (enable the hook)
- `CIHUB_MAX_ITERATIONS=10`
- `CIHUB_OUTPUT_DIR=.cihub`
- `CIHUB_REPO=.` (optional repo path)
- `CIHUB_AI_LOOP_FIX_MODE=safe|report-only`
- `CIHUB_AI_LOOP_EMIT_REPORT=true|false`
- `CIHUB_AI_LOOP_ITERATION` (set by hook)
- `CIHUB_AI_LOOP_MAX_ITERATIONS` (set by hook)

## Behavior

- Runs `cihub ci --json` with `CIHUB_EMIT_TRIAGE=true` to generate triage bundles
- Applies `cihub fix --safe` when `fix_mode=safe`
- Emits AI report packs with `cihub fix --report --ai` when `fix_mode=report-only`
  or `CIHUB_AI_LOOP_EMIT_REPORT=true`
- Exits `2` to keep Claude Code iterating until max iterations are reached
