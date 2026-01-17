# ADR-0029: CLI Exit Code Registry

**Status**: Accepted  
**Date:** 2025-12-26  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The CLI is now a stable integration surface (and the backend for the planned
PyQt6 GUI). Consumers need consistent exit codes to distinguish usage errors,
validation failures, user cancellations, and internal errors.

Historically, commands returned numeric literals directly, which makes it easy
for similar error cases to drift across commands.

## Decision

Define a single exit code registry and require commands to use it.

Registry (implemented in `cihub/exit_codes.py`):

| Code | Name | Meaning |
|------|------|---------|
| 0 | `EXIT_SUCCESS` | Success |
| 1 | `EXIT_FAILURE` | Command failed (validation/runtime) |
| 2 | `EXIT_USAGE` | Invalid usage or unmet precondition |
| 3 | `EXIT_DECLINED` | User declined a confirmation |
| 4 | `EXIT_INTERNAL_ERROR` | Unhandled internal error |
| 130 | `EXIT_INTERRUPTED` | Interrupted by user (SIGINT / wizard cancel) |

All commands must return these constants (or derive them) and JSON mode must
expose the same `exit_code` value in the response envelope.

## Consequences

**Positive:**
- Stable, documented exit codes for automation and GUI integration
- Fewer inconsistencies across commands
- Clear distinction between user intent and command failure

**Negative:**
- Requires updating existing commands to use the registry
- Slightly more boilerplate imports in command handlers

## Alternatives Considered

1. **Keep numeric literals in each command**
 - Rejected: prone to drift and harder to document.

2. **Use only two exit codes (0/1)**
 - Rejected: loses important signal (usage errors vs user cancel vs internal).

