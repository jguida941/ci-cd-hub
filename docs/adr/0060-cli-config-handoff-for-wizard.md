# ADR-0060: CLI Config Handoff for Interactive Wizards
Status: accepted
Date: 2026-01-19

## Context

The TypeScript interactive CLI must be a UX layer over the Python CLI and schema,
without re-implementing config generation logic. The existing Python wizard flows
(`cihub init --wizard`, `cihub new --interactive`, `cihub config edit`) are
terminal-interactive and reject `--json`, so the TypeScript wizard cannot use them
directly. We need a headless handoff path that lets the TypeScript wizard submit a
fully-formed config payload to the Python CLI while keeping the Python CLI as the
single source of truth for file writes and validation.

## Decision

Add a CLI-supported config handoff surface that accepts full config payloads as
either inline JSON or a YAML/JSON file:

- `cihub init --config-json ...` / `--config-file ...`
- `cihub new --config-json ...` / `--config-file ...`
- `cihub config edit --config-json ...` / `--config-file ...`

When config input is provided, the commands bypass interactive wizard prompts and
operate in JSON mode, allowing the TypeScript wizard to submit selections without
duplicating logic. `config edit` now supports JSON runtime when a config payload is
provided.

## Consequences

- CLI surface changes (new flags) are now part of the command contract and must be
documented and snapshot-tested.
- TypeScript wizard can hand off full configs to the Python CLI, preserving the
architecture requirement that the CLI remains the execution engine.
- The Python CLI remains responsible for writing config files and workflows, which
keeps behavior consistent across CLI, workflows, and GUI frontends.

## Alternatives Considered

1. **Rebuild config generation logic in TypeScript.** Rejected: violates the
   “wizard is a UX layer over handlers + schema” rule and risks drift.
2. **Invoke the Python interactive wizard from the TypeScript CLI.** Rejected:
   interactive TTY handling is unreliable within Ink and does not support JSON
   output.
3. **Introduce a new `config apply` command instead of extending `config edit`.**
   Rejected for now to keep the surface minimal; the new flags already provide a
   non-interactive apply path.
