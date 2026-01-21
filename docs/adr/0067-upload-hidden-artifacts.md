# ADR-0067: Upload Hidden CI Artifacts
Status: accepted
Date: 2026-01-21

## Context

CI outputs are written to `.cihub/`, which is a hidden directory by design.
GitHub Actions `upload-artifact` skips hidden files unless explicitly enabled,
so reusable workflows were failing to upload `.cihub/report.json` and related
artifacts. This blocked remote triage and verification.

## Decision

Set `include-hidden-files: true` on artifact upload steps in the hub’s reusable
workflows (java-ci.yml, python-ci.yml) so `.cihub` outputs are reliably
uploaded.

## Consequences

- Remote triage can always download report artifacts.
- Workflows stay thin; no extra copy steps are required.
- The `.cihub` output contract remains intact.

## Alternatives Considered

1. **Change output dir to non-hidden.** Rejected: breaks the CLI contract and
   requires changes across tools and docs.
2. **Add copy steps in workflows.** Rejected: adds logic to workflows instead
   of keeping it in the CLI.
