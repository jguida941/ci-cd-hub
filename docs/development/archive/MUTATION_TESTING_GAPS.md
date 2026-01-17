# Testing Priority Analysis (SDLC Complexity Study)
> **Superseded by:** [MASTER_PLAN.md](../MASTER_PLAN.md)  

> **WARNING: SUPERSEDED:** This analysis is archived. Testing priorities are now tracked in `docs/development/active/TEST_REORGANIZATION.md`.
>
> **Status:** Archived  

This document identifies high-risk code areas in `cihub/` based on cyclomatic complexity and SDLC best practices. Areas with high complexity correlate strongly with defect density and require focused testing.

---

## SDLC Research Summary

### Key Findings

| Principle | Source |
|-----------------------------------------------------------|--------------------------------|
| Bugs found later in SDLC cost 100x more to fix | IBM Systems Sciences Institute |
| High cyclomatic complexity correlates with defect density | Sonar, NASA |
| Complexity >20 = high risk, >50 = untestable | Industry standard |
| Testing reduces defects by 80-90% | Pluralsight SDLC Study |

### Cyclomatic Complexity Thresholds

| Score | Risk Level | Action |
|-------|------------|----------------------------|
| 1-10 | Low | Acceptable |
| 11-20 | Medium | Needs testing |
| 21-50 | High | Intensive testing required |
| 50+ | Very High | Refactor immediately |

---

## cihub Module Complexity Analysis

### Priority 1: `cihub/cli.py` (40KB) - CRITICAL

Estimated complexity: **50+** (Very High)

| Function | Lines | Complexity | Risk |
|--------------------------------------|----------|------------|-----------|
| `parse_pom_plugins()` | 151-184 | ~15 | HIGH |
| `parse_pom_dependencies()` | 204-230 | ~12 | HIGH |
| `collect_java_pom_warnings()` | 244-302 | ~25 | VERY HIGH |
| `collect_java_dependency_warnings()` | 316-372 | ~20 | HIGH |
| `insert_plugins_into_pom()` | 421-464 | ~18 | HIGH |
| `insert_dependencies_into_pom()` | 477-500+ | ~15 | HIGH |

**Why high risk:**
- XML namespace handling with multiple code paths
- Regex-based string manipulation
- Multi-module Maven project detection
- Error recovery branches

### Priority 2: `cihub/commands/secrets.py` (8.5KB) - HIGH

Estimated complexity: **25-35**

| Function | Complexity | Risk |
|------------------------------|------------|--------|
| `cmd_setup_secrets()` | ~20 | HIGH |
| `cmd_setup_nvd()` | ~18 | HIGH |
| `verify_token()` | ~8 | MEDIUM |
| `verify_cross_repo_access()` | ~8 | MEDIUM |

**Why high risk:**
- External API calls (GitHub, NVD)
- Subprocess execution (`gh secret set`)
- Multiple HTTP error handling branches
- Token validation logic

### Priority 3: `cihub/commands/templates.py` (5.5KB) - HIGH

Estimated complexity: **20-30**

| Function | Complexity | Risk |
|------------------------|------------|-----------|
| `cmd_sync_templates()` | ~25 | VERY HIGH |

**Why high risk:**
- Remote file operations (fetch, update, delete)
- Stale workflow detection and cleanup
- Git tag manipulation
- 7+ decision branches in main function

### Priority 4: `cihub/config/io.py` (4.7KB) - MEDIUM

Estimated complexity: **5-10** (Low)

Simple file I/O functions. Adequately tested.

### Priority 5: `cihub/config/merge.py` (3KB) - MEDIUM

Estimated complexity: **5-8** (Low)

Recursive dict merge. Adequately tested.

---

## Testing Gap Analysis

### Before (2025-12-26)

| Module | Size | Est. Complexity | Tests | Gap |
|-----------------|-------|-----------------|-------|--------------|
| `cli.py` | 40KB | 50+ | 12 | **CRITICAL** |
| `secrets.py` | 8.5KB | 25-35 | 0 | **CRITICAL** |
| `templates.py` | 5.5KB | 20-30 | ~10 | HIGH |
| `config_cmd.py` | 5KB | 15-20 | 0 | MEDIUM |
| `io.py` | 4.7KB | 5-10 | ~15 | OK |
| `merge.py` | 3KB | 5-8 | ~19 | OK |

### After (Tests Added)

| Module | New Tests | Coverage |
|------------------------|-------------------------------------|------------------------------------------------------------------------|
| `cli.py` (POM parsing) | **+46** (`test_pom_parsing.py`) | XML utilities, plugin parsing, dependency parsing, warnings, insertion |
| `secrets.py` | **+19** (`test_secrets.py`) | Token validation, API verification, cross-repo access, secret setting |
| `templates.py` | **+9** (`TestSyncTemplatesCommand`) | Sync modes, drift detection, stale cleanup |

**Total tests: 356** (up from ~280)

---

## Test Implementation Plan

### Phase 1: `tests/test_pom_parsing.py` (~20 tests)

Target functions in `cihub/cli.py`:

```
- parse_pom_plugins(): namespace handling, error paths
- parse_pom_dependencies(): dependency extraction
- collect_java_pom_warnings(): multi-branch logic
- insert_plugins_into_pom(): regex, 3 code paths
- insert_dependencies_into_pom(): similar complexity
```

Test cases:
- POM with/without XML namespace
- Multi-module Maven projects
- Missing/malformed XML
- Plugin insertion into existing vs new `<build>` section
- Empty pom.xml handling
- Unusual indentation patterns

### Phase 2: `tests/test_secrets.py` (~15 tests)

Target functions in `cihub/commands/secrets.py`:

```
- cmd_setup_secrets(): token setup flow
- cmd_setup_nvd(): NVD key setup flow
- verify_token(): GitHub API verification
- verify_cross_repo_access(): artifact access check
```

Test cases (with mocking):
- Token with leading/trailing whitespace
- Token with embedded whitespace (should fail)
- GitHub API 401/403/timeout responses
- NVD API 200/403/timeout responses
- `gh secret set` success/failure
- Cross-repo access verification

### Phase 3: Extend `tests/test_templates.py` (~10 tests)

Target functions in `cihub/commands/templates.py`:

```
- cmd_sync_templates(): full sync flow
```

Test cases:
- Remote file matches desired (no update needed)
- Remote file differs (update required)
- Stale workflow deletion
- `--check` mode behavior
- `--dry-run` mode behavior
- Git tag update success/failure

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=cihub --cov-report=html

# Run mutation testing (when practical)
mutmut run --paths-to-mutate=cihub/cli.py
```

---

## References

- [Sonar: Cyclomatic Complexity Guide](https://www.sonarsource.com/resources/library/cyclomatic-complexity/)
- [LinearB: Cyclomatic Complexity Explained](https://linearb.io/blog/cyclomatic-complexity)
- [NASA: Excessive Cyclomatic Complexity](https://swehb.nasa.gov/display/SITE/R014+-+Excessive+Cyclomatic+Complexity+On+Safety+-+Critical+Software+Components)
- [Functionize: Cost of Finding Bugs Later](https://www.functionize.com/blog/the-cost-of-finding-bugs-later-in-the-sdlc)
- [Pluralsight: SDLC Best Practices](https://www.pluralsight.com/resources/blog/software-development/SDLC-best-practices)

---

**Last Updated:** 2025-12-26
