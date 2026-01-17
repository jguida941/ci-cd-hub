# ADR-0047: Config Validation Order

**Status**: Accepted  
**Date:** 2026-01-06  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-06  

## Context

The config loading system merges configuration from multiple sources:
1. `config/defaults.yaml` (lowest priority)
2. `config/repos/<repo>.yaml` (hub override)
3. `.ci-hub.yml` in repo (highest priority)

Each layer is normalized before merging, then the final merged config is validated.

**Problem:** The original implementation only validated the final merged config:

```python
# BEFORE (problematic)
config = load_yaml(defaults_path)
config = normalize_config(config) # Normalization might mask invalid values

repo_override = normalize_config(load_yaml(repo_override_path))
config = deep_merge(config, repo_override)

# Validation only happens here - invalid input may be normalized away
validate_config(config, "merged-config")
```

This created a correctness issue:
1. User provides invalid config value (e.g., `thresholds: "high"` instead of `thresholds: {coverage_min: 70}`)
2. Normalization converts or ignores the invalid value
3. Validation sees the normalized (valid-looking) config
4. Invalid input is silently accepted

## Decision

**Validate BEFORE normalize** at each layer to catch invalid input early:

```python
# AFTER (correct)
config = load_yaml(defaults_path)
validate_config(config, "defaults (pre-normalize)") # Catch invalid defaults
config = normalize_config(config)

repo_override_raw = load_yaml(repo_override_path)
if repo_override_raw:
 validate_config(repo_override_raw, "hub override (pre-normalize)") # Catch invalid override
repo_override = normalize_config(repo_override_raw)
config = deep_merge(config, repo_override)

repo_local = load_yaml(repo_config_path)
if repo_local:
 validate_config(repo_local, "repo local (pre-normalize)") # Catch invalid local config
repo_local = normalize_config(repo_local)
config = deep_merge(config, repo_local)

# Final validation on merged result
validate_config(config, "merged-config")
```

### Validation Flow

```
┌─────────────────┐
│ Load defaults │
└────────┬────────┘
 │
 ▼
┌─────────────────┐
│ Validate (pre) │ ◄── Catch invalid defaults early
└────────┬────────┘
 │
 ▼
┌─────────────────┐
│ Normalize │
└────────┬────────┘
 │
 ▼
┌─────────────────┐
│ Load override │
└────────┬────────┘
 │
 ▼
┌─────────────────┐
│ Validate (pre) │ ◄── Catch invalid repo config early
└────────┬────────┘
 │
 ▼
┌─────────────────┐
│ Normalize │
└────────┬────────┘
 │
 ▼
┌─────────────────┐
│ Merge │
└────────┬────────┘
 │
 ▼
┌─────────────────┐
│ Validate (post) │ ◄── Verify merged result is valid
└─────────────────┘
```

### Error Messages

Error messages now indicate which layer and stage failed:

```
Config validation failed for hub override (fixtures-python.yaml, pre-normalize):
 - thresholds.coverage_min: 'high' is not of type 'number'
```

This makes debugging much easier than:

```
Config validation failed for merged-config:
 - (no errors because normalization fixed it)
```

## Consequences

### Positive

- **Early error detection**: Invalid config caught at source, not hidden by normalization
- **Clear error messages**: User knows exactly which file and field is wrong
- **Debugging support**: Pre-normalize errors point to actual user input
- **Schema adherence**: Config must be schema-valid before any processing

### Negative

- **More validation calls**: Each layer validated separately (3 pre + 1 post)
- **Slightly slower**: ~10-20ms overhead for additional schema checks
- **Stricter**: Some previously-accepted malformed configs now fail

### Migration Notes

Existing configs that relied on normalization to "fix" invalid values will now fail validation. This is intentional - configs should be valid before normalization.

## Test Coverage

- Add tests for invalid config at each layer
- Add tests that verify error messages include layer name
- Add tests that normalization doesn't mask validation errors

## Files Changed

- `cihub/config/loader/core.py` - Validation order fix

## Related ADRs

- ADR-0002: Config Precedence (merge order)
- ADR-0020: Schema Backward Compatibility (schema evolution)
- ADR-0028: Boolean Config Type Coercion (normalization rules)
