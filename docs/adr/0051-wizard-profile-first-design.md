# ADR-0051: Wizard Profile-First Design

**Status**: Proposed
**Date:** 2026-01-08
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-08

## Context

The CIHub wizard currently asks users to enable/disable each tool individually (13+ prompts for Python). This is:
- Tedious for users
- Error-prone (easy to misconfigure)
- Doesn't leverage existing profiles (`fast`, `quality`, `security`, etc.)
- Makes the wizard feel "class-project" rather than "enterprise"

We have 6 well-designed profiles per language in `templates/profiles/` that encode best practices:

| Profile | Tools Enabled | Runtime |
|---------|--------------|---------|
| `minimal` | pytest, ruff | ~2-5 min |
| `fast` | pytest, ruff, black, isort, bandit, pip-audit | ~3-8 min |
| `quality` | fast + mypy, mutmut | ~15-30 min |
| `security` | bandit, pip-audit, semgrep, trivy, codeql | ~15-30 min |
| `compliance` | security + stricter thresholds | ~15-30 min |
| `coverage-gate` | high coverage/mutation requirements | ~12-20 min |

## Decision

### Primary Decision: Profile-First Selection + Individual Tool Customization

The wizard presents profiles as a **starting point**, then ALWAYS shows individual tool checkboxes for customization:

```
Step 3: Select Starting Profile
  ○ Fast (Recommended) - Quick PR feedback (~5 min)
  ○ Quality - Thorough analysis with mutation testing (~20 min)
  ○ Strict - Full security scanning and compliance (~30 min)
  ○ Start from scratch

Step 4: Configure Tools (always shown, pre-filled by profile)
  ☑ pytest       (enabled by Fast profile)
  ☑ ruff         (enabled by Fast profile)
  ☑ black        (enabled by Fast profile)
  ☐ isort        (click to add)
  ☐ mypy         (click to add)
  ☑ bandit       (enabled by Fast profile)
  ☑ pip_audit    (enabled by Fast profile)
  ...
```

**Key principle:** Profiles are defaults/templates, not restrictions. Users ALWAYS have full control via checkboxes.

### Sub-Decision 1: Black/isort Mode (Q1)

**Decision:** Default to `check` mode in CI.

- CI runs `black --check` and `isort --check` (fail if not formatted)
- Users run `cihub fix --format` locally to auto-fix
- Rationale: Auto-fixing in CI can surprise users; explicit is better than implicit

### Sub-Decision 2: Config Location (Q2)

**Decision:** All CI config stays in `.ci-hub.yml`

- `.ci-hub.yml` is the single source of truth for CI behavior
- Users can manually create `pyproject.toml` tool sections for IDE integration
- Rationale: Splitting config across files creates sync issues

### Sub-Decision 3: Multi-CI Support (Q3)

**Decision:** GitHub Actions is the primary and only supported CI for v1.0

- GitLab CI, CircleCI, etc. are out of scope for v1.0
- May add in v2.0 based on user demand
- Rationale: Focus on doing one thing well

## Alternatives Considered

### Profile Selection
- **Individual tool prompts only (current):** Works but tedious - doesn't leverage profiles
- **Profiles only, no customization:** Rejected - power users need fine control
- **Profile selection + always show checkboxes:** ACCEPTED - best of both worlds

### Black Mode
- **Default to auto-fix:** Rejected - modifying files in CI can surprise users
- **Always ask:** Acceptable, but adds friction for common case

### Config Location
- **Split to pyproject.toml:** Rejected - creates sync issues, harder to validate
- **Generate both:** Rejected - maintenance burden, risk of drift

## Consequences

### Positive
- Wizard becomes 3-4 prompts instead of 15+ for most users
- Profiles encode team best practices
- "Custom" still available for power users
- Check mode is safer default for CI

### Negative
- Need to maintain profile-to-wizard mapping
- Users expecting individual prompts may be confused initially
- Check mode means local `black .` required before commit

### Neutral
- Profile files become more important - any profile bug affects all wizard users
- May need "profile preview" to show what tools are enabled

## Implementation Notes

Files to modify:
- `cihub/wizard/core.py` - Add profile selection step
- `cihub/wizard/questions/profile.py` (new) - Profile selection prompts
- `cihub/wizard/questions/python_tools.py` - Make conditional on "Custom"
- `cihub/wizard/questions/java_tools.py` - Make conditional on "Custom"
- `cihub/commands/setup.py` - Integrate profile selection

## Related ADRs

- ADR-0007: Templates and Profiles Strategy
- ADR-0006: Quality Gates and Thresholds
