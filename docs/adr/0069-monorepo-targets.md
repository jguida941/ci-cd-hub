# ADR-0069: Monorepo Targets in .ci-hub.yml
Status: accepted
Date: 2026-01-21

## Context

`repo.subdir` supports a single language/subdir per repo. Monorepos that contain
both Python and Java projects need multi-target runs so the CLI can execute the
right tools per subdir without repo-specific workflow edits.

## Decision

Add `repo.targets` as an array of `{language, subdir}` pairs. When present,
`cihub ci` iterates targets, runs each target in its own output directory, and
emits an aggregate `report.json` with a `targets` list of per-target reports.
Summary rendering uses per-target sections.

`--workdir` remains a single-target override. `repo.subdir` stays supported for
single-target repos and is ignored when `repo.targets` is present.

## Consequences

- Monorepos can run multiple language toolchains in one CLI invocation.
- Aggregated reports are accurate per target without losing top-level metadata.
- Workflows may need to ensure the runtime environment supports all target
  languages.

## Alternatives Considered

1. **Keep only `repo.subdir`.** Rejected: cannot express multi-language repos.
2. **Require separate workflows per subdir.** Rejected: breaks CLI-first model.
