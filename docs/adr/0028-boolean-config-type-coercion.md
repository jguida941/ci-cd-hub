# ADR-0028: Boolean Config Type Coercion

**Status**: Accepted  
**Date:** 2025-12-26  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

Boolean configuration values (tool toggles like `run_jacoco`, `run_pytest`) flow through multiple layers with different type systems:

1. **YAML Config** (`config/repos/*.yaml`, `.ci-hub.yml`) - Native YAML booleans (`enabled: true`)
2. **Python** (`cihub/cli.py`) - Python `bool` type
3. **CLI env overrides** (`CIHUB_RUN_*`, `CIHUB_WRITE_GITHUB_SUMMARY`) - Strings, parsed to `bool`
4. **GITHUB_OUTPUT** - String output (`echo "run_jacoco=true"`)
5. **JavaScript** (orchestrator) - String environment variables, converted via `asBool()`
6. **workflow_dispatch API** - Expects strings `'true'`/`'false'` for boolean inputs
7. **Reusable Workflow Inputs** - Declared as `type: boolean`, GitHub auto-converts strings

This type coercion chain caused a bug where summary tables in `java-ci.yml` showed "Ran: false" for all tools regardless of actual execution state.

### Root Cause

The bug was in workflow expression comparisons:

```yaml
# WRONG - comparing boolean input to string literal
${{ inputs.run_jacoco == 'true' && steps.jacoco.outcome == 'success' }}

# CORRECT - comparing boolean input to boolean literal
${{ inputs.run_jacoco == true && steps.jacoco.outcome == 'success' }}
```

When `inputs.run_jacoco` is declared as `type: boolean`, GitHub Actions interprets the value as a boolean. Comparing it to the string `'true'` always fails.

## Decision

**Boolean comparison rules by context:**

| Context | Type | Comparison | Example |
|---------|------|------------|---------|
| Workflow `if:` condition | Boolean | Implicit truthy | `if: inputs.run_jacoco` |
| Workflow expression `${{ }}` | Boolean | Compare to `true`/`false` literal | `${{ inputs.run_jacoco == true }}` |
| Shell script after interpolation | String | Compare to `"true"`/`"false"` | `if [ "${{ inputs.run_jacoco }}" = "true" ]` |
| Step outputs | String | Compare to `'true'`/`'false'` | `steps.check.outputs.exists == 'true'` |
| Job result | String | Compare to `'success'`/`'failure'` | `needs.lint.result == 'success'` |

**Key insight:** Step outputs and job results are always strings, but workflow `inputs` declared as `type: boolean` are actual booleans.

### Type Coercion Pipeline

```
YAML Config (bool)
 ↓
Python loads (bool)
 ↓
CLI env overrides (CIHUB_RUN_* / CIHUB_WRITE_GITHUB_SUMMARY)
 ↓
Python writes to GITHUB_OUTPUT (string "true"/"false")
 ↓
JavaScript reads env var (string)
 ↓
asBool() normalizes to 'true'/'false' string
 ↓
workflow_dispatch API receives string
 ↓
GitHub converts to boolean (type: boolean input)
 ↓
Workflow uses native boolean
```

The `asBool()` helper in the orchestrator handles various truthy representations:

```javascript
function asBool(value) {
 if (typeof value === 'boolean') return value ? 'true' : 'false';
 const s = String(value).toLowerCase().trim();
 return ['true', '1', 'yes', 'on'].includes(s) ? 'true' : 'false';
}
```

## Alternatives Considered

1. **Keep string comparisons everywhere:**
 Rejected. Error-prone and inconsistent with GitHub Actions' type system.

2. **Use only implicit truthy checks:**
 ```yaml
 ${{ inputs.run_jacoco && steps.jacoco.outcome == 'success' }}
 ```
 This works but is less explicit. We chose explicit `== true` for clarity.

3. **Convert all inputs to strings:**
 Rejected. Loses type safety and breaks dispatch UI checkboxes.

## Consequences

**Positive:**
- Summary tables now correctly show which tools ran
- Clear documentation of type expectations at each layer
- Consistent pattern across Java and Python workflows

**Negative:**
- Must audit all boolean comparisons when adding new tools
- Different comparison syntax needed in shell vs workflow expressions

## Implementation

Files changed:
- `.github/workflows/java-ci.yml` - Lines 582-590: Changed `== 'true'` to `== true` in summary table
- `.github/workflows/python-ci.yml` - Already correct (uses `== true`)

### Correct Patterns

**Workflow conditions:**
```yaml
# Good - implicit truthy
if: inputs.run_jacoco

# Good - explicit boolean comparison
if: inputs.run_jacoco == true

# Bad - string comparison for boolean input
if: inputs.run_jacoco == 'true'
```

**Inline expressions:**
```yaml
# Good - boolean comparison
${{ inputs.run_jacoco == true && 'Enabled' || 'Disabled' }}

# Bad - string comparison
${{ inputs.run_jacoco == 'true' && 'Enabled' || 'Disabled' }}
```

**Shell scripts (after `${{ }}` interpolation):**
```bash
# Good - string comparison (value already interpolated to string)
if [ "${{ inputs.run_jacoco }}" = "true" ]; then

# Also good - same thing
if [ "${{ inputs.run_jacoco }}" != "true" ]; then
```

**Step outputs (always strings):**
```yaml
# Good - step outputs are strings
if: steps.check-dockerfile.outputs.exists == 'true'
```

## References

- ADR-0024: Workflow Dispatch Input Limit
- ADR-0006: Quality Gates and Thresholds
- GitHub docs: [Workflow syntax - inputs](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs)
