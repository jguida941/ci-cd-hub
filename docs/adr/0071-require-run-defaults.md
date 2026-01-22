# ADR-0071: Require Configured Tools to Run by Default
Status: accepted
Date: 2026-01-22

## Context

CI reports must be trustworthy: if a tool is configured, it should run and
produce evidence. The current defaults allow configured tools to be treated as
optional, which hides gaps and makes audit results ambiguous. This is
especially problematic in production onboarding and when validating a broad
repo matrix.

## Decision

Set `require_run_or_fail` defaults to `true` for all tools, and set the global
`gates.require_run_or_fail` default to `true`. Users may still opt out per tool
by explicitly setting `require_run_or_fail: false` in config.

## Consequences

- Configured tools that do not run are now treated as failures by default.
- Tool evidence and reports must be generated for all configured tools.
- Repo owners retain the ability to mark specific tools as optional.

## Alternatives Considered

1. **Keep current optional defaults.** Rejected: configured tools can be
   skipped without surfacing failures, which undermines audit confidence.
2. **Apply the change only to select tools.** Rejected: creates inconsistent
   behavior and reduces predictability across repos.
