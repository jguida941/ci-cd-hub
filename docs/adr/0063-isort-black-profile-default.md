# ADR-0063: Default isort Profile to Black
**Status:** Accepted  
**Date:** 2026-01-19  

## Context

cihub runs isort in check mode for Python repos. Many repos follow Black
formatting, but isort defaults can still produce diffs unless the repo
declares a compatible profile. Relying on repo-local changes (e.g.,
`[tool.isort]` in pyproject.toml) breaks the CLI-first contract and
forces manual edits to get CI green.

## Decision

Run isort with `--profile black` when Black is enabled in the cihub config.
This aligns isort's import formatting with Black for repos that opt into
Black, without requiring repo-specific configuration.

## Consequences

- Black-formatted repos pass isort checks without extra config.
- The CLI remains the source of truth; no repo-specific config is required
  to reconcile Black/isort defaults.
- Repos that intentionally diverge can still override via future config
  options if needed.

## Alternatives Considered

1. **Require repos to add `[tool.isort]` settings.** Rejected: violates
   CLI-first onboarding and forces repo edits for a standard behavior.
2. **Add a new schema option before changing defaults.** Deferred: might
   be useful later, but an immediate default fix unblocks CI now.
