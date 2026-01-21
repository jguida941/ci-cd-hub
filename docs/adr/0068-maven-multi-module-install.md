# ADR-0068: Maven Multi-Module Install Prep
Status: accepted
Date: 2026-01-21

## Context

Multi-module Maven repos can fail tool runs (PMD/SpotBugs/PITest/OWASP) because
their plugin executions run in a fresh Maven invocation that cannot resolve
reactor-built artifacts. This shows up as missing module dependencies in CI
even after a successful build step.

## Decision

For Maven multi-module projects, cihub will run a lightweight install step
(`mvn -DskipTests install`) after the build and before Maven plugin tools when
any of those tools are enabled. This keeps the fix inside the CLI and avoids
repo-specific edits.

## Consequences

- Multi-module tool runs can resolve reactor artifacts without manual repo
  changes.
- Additional Maven install step adds a small time cost but prevents repeated
  CI failures.
- No workflow or repo config changes are required.

## Alternatives Considered

1. **Modify repos to add install steps.** Rejected: violates CLI-first.
2. **Skip Maven tools on multi-module repos.** Rejected: hides real issues.
