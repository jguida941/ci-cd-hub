# ADR-0033: CLI Distribution and Automation Enhancements

**Status**: Accepted  
**Date:** 2025-12-26  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

With ADR-0031/0032, the CLI (`cihub`) becomes the execution engine and GUI
backend. This requires a clear distribution strategy, standardized parsing for
custom commands, and automation around secrets, private dependencies, and repo
management. We also need to document workflow limits and validation tooling so
the new architecture stays stable.

## Decision

Adopt the following decisions as part of the CLI-driven architecture:

### Distribution Strategy

- Publish `cihub` to PyPI.
- Use scoped PyPI tokens (not global API keys).
- Automated release workflow builds (`python -m build`) and uploads via `twine`.
- Use semantic versioning and tags; workflows should pin to tags (e.g., `@v1`).

### Custom Command Parsing

Support three parsing modes for custom commands:

- `exit_code`: success/failure by return code.
- `json`: parse structured output.
- `regex`: extract metrics by pattern.

Example config:
```yaml
python:
  tools:
    custom:
      - name: "make-test"
        command: "make test"
        parser: "exit_code"
      - name: "coverage-json"
        command: "coverage json -o coverage.json"
        parser: "json"
        metric_path: "totals.percent_covered"
```

### Private Dependency Auth

- Python: set `PIP_INDEX_URL` with secret-backed credentials.
- Maven: use base64-encoded `settings.xml` stored as a secret and decoded at runtime.

### Secrets Automation

Provide CLI commands to:
- set secrets (single or bulk from env file),
- verify required secrets exist,
- discover required secrets from config/workflows.

### Workflow Limits

Document and enforce:
- 10 levels of reusable workflow nesting.
- 50 unique workflow calls per workflow file.
- Production callers must pin tags, not `@main`.

### Schema Validation

Adopt `check-jsonschema` for `.ci-hub.yml` validation and integrate with
pre-commit where possible.

### CLI Framework Choice

Keep `argparse` for base CLI (stdlib, zero deps). Revisit Typer/Click only if
maintainability becomes a blocker.

## Consequences

**Positive:**
- Clear, versioned distribution path for workflows and GUI users.
- Standardized parsing for custom commands and Makefile integration.
- Automation for secrets and private dependency access.
- Stronger validation and reduced drift.

**Negative:**
- Release workflow becomes a required dependency.
- Adds operational overhead for PyPI publishing and token management.
- Custom parsing modes add complexity to the CLI codebase.

## Alternatives Considered

1. **Install from GitHub URLs only**
   - Rejected: less stable, requires PATs for private repos.

2. **Keep parsing inside workflows**
   - Rejected: inline scripts remain large and hard to test.

3. **Use Click/Typer immediately**
   - Rejected: adds dependency; `argparse` is sufficient for now.

## References

- https://www.loopwerk.io/articles/2025/automate-python-releases/
- https://github.com/kellyjonbrazil/jc
- https://pip.pypa.io/en/stable/topics/authentication/
- https://cli.github.com/manual/gh_secret_set
- https://github.com/python-jsonschema/check-jsonschema
- https://docs.github.com/en/actions/concepts/workflows-and-actions/reusable-workflows
