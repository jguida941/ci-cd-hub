# ADR-0070: Tool Evidence in CI Reports
Status: accepted
Date: 2026-01-21

## Context

Reports sometimes claim tools ran or succeeded when no metrics or artifacts
exist. This makes the summary tables look green even when the run produced no
evidence. We need a consistent, CLI-owned signal that ties tool status to
evidence produced.

## Decision

Add a `tool_evidence` boolean map to `report.json`. Evidence is true when a tool
produces report metrics or artifacts (including `report_found` metrics). If a
tool ran but evidence is missing, summaries show `NO REPORT` and validators emit
warnings. Java tool runners treat missing reports as failures.

## Consequences

- Report consumers can reliably detect “ran but no proof” cases.
- Tools without report output must emit metrics or artifacts to be considered
  successful.

## Alternatives Considered

1. **Trust `tools_success` alone.** Rejected: hides missing evidence.
2. **Workflow-only artifact checks.** Rejected: breaks CLI-first contract.
