# Documentation Automation Guide

**Status:** reference  
**Owner:** Development Team  
**Source-of-truth:** manual  
**Last-reviewed:** 2026-01-17  

## Purpose

Keep documentation accurate by running the CLI doc automation commands and letting the CLI generate the reference docs. This guide covers the required commands, outputs, and common workflows.

## Do Not Edit Generated Docs

These files are generated and should not be edited by hand:
- `docs/reference/CLI.md`
- `docs/reference/CONFIG.md`
- `docs/reference/ENV.md`
- `docs/reference/WORKFLOWS.md`

## Required Doc Gates (Run After Any Doc Change)

```bash
cihub docs generate
cihub docs check
cihub docs stale
cihub docs audit
```

**What they do:**
- `cihub docs generate` regenerates reference docs from the CLI and schema.
- `cihub docs check` verifies generated docs are current.
- `cihub docs stale` scans docs for stale code references.
- `cihub docs audit` validates lifecycle rules, headers, ADR metadata, and doc consistency.

## Optional Checks (When Relevant)

```bash
cihub docs links
```

Use this to validate internal links before releases or when a large refactor touches many doc paths.

## Automation Outputs (Artifacts)

Use `--output-dir` to capture JSON artifacts:

```bash
cihub docs stale --output-dir .cihub/tool-outputs
cihub docs audit --output-dir .cihub/tool-outputs
```

Artifacts written:
- `.cihub/tool-outputs/docs_stale.json`
- `.cihub/tool-outputs/docs_stale.prompt.md`
- `.cihub/tool-outputs/docs_audit.json`

## Tests README Generation

`tests/README.md` is generated from test metrics. Regenerate it after test structure changes:

```bash
cihub hub-ci test-metrics --write
```

## Common Workflows

**Update reference docs:**
```bash
cihub docs generate
cihub docs check
```

**Full doc validation (pre-push):**
```bash
cihub docs generate
cihub docs check
cihub docs stale
cihub docs audit
```

**Fast audit (skip slow scans):**
```bash
cihub docs audit --skip-references --skip-consistency
```

## Troubleshooting

- **"Docs are out of date"**: Run `cihub docs generate`, then `cihub docs check`.
- **Stale references found**: Update doc paths or fix the code reference; rerun `cihub docs stale`.
- **Audit header failures**: Ensure doc headers include `Status/Owner/Source-of-truth/Last-reviewed` with line breaks.
- **Header lines collapsing**: Run `python scripts/normalize_doc_headers.py` to reapply two-space line breaks.

## Related Docs

- `docs/development/archive/DOC_AUTOMATION_AUDIT.md` (design + implementation status)
- `docs/guides/CLI_EXAMPLES.md` (examples for doc commands)
