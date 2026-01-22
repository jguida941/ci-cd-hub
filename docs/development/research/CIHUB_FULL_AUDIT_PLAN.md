# CIHub Full Audit Plan

**Status:** active
**Owner:** Development Team
**Source-of-truth:** manual
**Last-reviewed:** 2026-01-23

## Purpose

Define a repeatable, CLI-first audit plan that proves CIHub works across repo shapes
and toolchains, with evidence that reported results match artifacts.

## Scope

- Python CLI (all commands, all tools)
- TypeScript CLI (command routing, passthrough, wizard, config handoff)
- Wizard (init/new/config edit flows, wizard metadata passthrough)
- Workflow entrypoints (hub-ci.yml, python-ci.yml, java-ci.yml)
- Orchestrator workflows (run-all, multi-repo dispatch/triage)
- Tool evidence and report verification (artifacts vs claims)

## Principles

- CLI-first: use cihub commands only; no manual YAML edits.
- No repo-specific hardcoding: fixes must generalize via schema, config, or detection.
- Evidence required: a tool is only "ran" if it produced expected artifacts/metrics.
- Stop-the-line: if any tool fails, fix the tool before moving to the next repo.
- Log everything: every command and result goes into the audit log.

## Evidence Rules

A tool is only counted as **ran** when:

- command executed (exit code captured)
- report artifacts exist in `.cihub/` or `.cihub/tool-outputs/`
- metrics are parsed and match the report content

If any evidence is missing:

- mark `NO PROOF`
- include paths checked and missing
- do not claim success

## Audit Repos (Initial Matrix)

Python:
- cihub-test-python-pyproject
- cihub-test-python-src-layout
- cihub-test-python-setup
- cihub-test-python
- gitui (PySide6 GUI)

Java:
- cihub-test-java-maven
- cihub-test-java-gradle
- cihub-test-java-multi-module
- java-spring-tutorials (multi-module, real world)

Monorepo:
- cihub-test-monorepo (python + java)

Orchestrator:
- ci-cd-hub-fixtures
- ci-cd-hub-canary-python
- ci-cd-hub-canary-java

## Command Audit Matrix

Core:
- cihub detect
- cihub init / setup / update
- cihub ci
- cihub run <tool>
- cihub config-outputs

Repo tooling:
- cihub fix-pom / fix-gradle
- cihub verify / triage / dispatch

Docs:
- cihub docs generate/check/stale/audit

## TypeScript CLI + Wizard Audit

- Confirm command routing for all Python CLI commands
- Verify `--config-json` handoff for init/new/config edit
- Verify passthrough flags (hub-repo/ref, set-hub-vars)
- Test non-interactive commands via TS CLI and compare outputs

## User Stories (Must Pass)

- New repo setup (Python, Java, Monorepo) via CLI only
- Same setup via TS CLI and wizard
- Repo with no tests: tool should report "no tests" and provide guidance
- Repo with GUI tests: headless config via CLI config
- Multi-module Java repo: OWASP and PITest run with report evidence
- Monorepo: per-target outputs, both languages run in one workflow

## Execution Plan

1. Prove fixtures and test repos green using delete -> init -> dispatch -> triage.
2. If any tool fails or lacks evidence, fix tool before next repo.
3. Run real-world repos (java-spring-tutorials, gitui).
4. Validate orchestrator (run-all + dispatch/triage) end-to-end.
5. Audit TS CLI + wizard command parity and log deltas.
6. Re-run a subset of repos to confirm repeatability.

## Audit Log

All commands and results go into:
- docs/development/research/CIHUB_TOOL_RUN_AUDIT.md

Each entry includes:
- repo, branch, toolchain
- commands executed
- run IDs and URLs
- pass/fail + evidence paths
- fixes applied (if any)

## Exit Criteria

- All commands tested for Python CLI, TS CLI, and wizard flows
- All tools produce evidence or fail with explicit reason
- No placeholder reports counted as success
- Reproducible green runs on the repo matrix
