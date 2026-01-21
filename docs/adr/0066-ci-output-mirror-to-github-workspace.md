# ADR-0066: Mirror CI Outputs to GITHUB_WORKSPACE
Status: accepted
Date: 2026-01-21

## Context

Reusable workflows run in a runner workspace that may not match the repo path
used by `cihub ci`. This can cause `.cihub` artifacts (report.json, summary.md,
tool outputs) to be written outside of `GITHUB_WORKSPACE`, which breaks the
workflow artifact upload step and downstream triage tooling.

## Decision

After a CI run completes, if `GITHUB_WORKSPACE` is set and the output directory
is outside that workspace, cihub mirrors the output directory into
`$GITHUB_WORKSPACE/<output_dir_name>` (typically `$GITHUB_WORKSPACE/.cihub`).

If mirroring fails, cihub emits a warning but continues.

## Consequences

- Artifact upload steps consistently find `.cihub` outputs in reusable workflows.
- Local behavior is unchanged when `GITHUB_WORKSPACE` is not set.
- The CLI remains the single source of truth for artifact generation.

## Alternatives Considered

1. **Edit workflows to add copy steps.** Rejected: workflow logic should remain thin.
2. **Require explicit output-dir paths in workflows.** Rejected: too error-prone.
