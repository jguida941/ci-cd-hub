# ADR-0050: Triage Command Modularization

**Status**: Implemented
**Date:** 2026-01-07
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-07
**Implementation:** Commits `4156a06` (Phase 1), `3a37c45` (Phases 2-3), current (Phase 4)

## Context

The `cihub/commands/triage.py` command file has grown to **1452 lines**, handling:

1. **GitHub API interactions** - Run info, downloads, listing runs
2. **Artifact processing** - Finding, extracting, parsing
3. **Log parsing** - Extracting failures from GitHub logs
4. **Remote triage** - Generating bundles from remote runs
5. **Tool verification** - Verifying configured vs ran vs success
6. **Output formatting** - Flaky output, gate history, verification reports
7. **Watch mode** - Polling for failures
8. **CLI routing** - Main `cmd_triage` entry point

This violates single responsibility principle and makes the code:
- Hard to test in isolation
- Difficult to extend
- Prone to merge conflicts
- Not reusable outside the triage command

### Current Pain Points

1. **Testing**: Can't test GitHub API helpers without mocking everything
2. **Complexity**: 1452 lines in one file
3. **Coupling**: Log parsing mixed with bundle generation
4. **No polymorphism**: Hard-coded conditionals instead of strategy pattern

## Decision

Modularize `cihub/commands/triage.py` into a package following the pattern from `hub_ci/` and `docs_stale/`:

### 1. Package Structure

```
cihub/commands/triage/
    __init__.py       # Main cmd_triage + routing (target: <300 lines)
    types.py          # Constants, severity maps, type aliases
    github.py         # GitHub API helpers (encapsulation)
    artifacts.py      # Artifact finding/processing (encapsulation)
    log_parser.py     # Log parsing for failures
    remote.py         # Remote bundle generation (strategy pattern)
    verification.py   # Tool verification (_verify_tools_from_report)
    output.py         # Formatting helpers
    watch.py          # Watch mode (single responsibility)
```

### 2. Design Patterns

#### Encapsulation (github.py)
```python
class GitHubRunClient:
    """Encapsulates GitHub API interactions."""

    def __init__(self, repo: str | None = None):
        self.repo = repo or self._detect_repo()

    def fetch_run_info(self, run_id: str) -> RunInfo:
        """Fetch run metadata."""
        ...

    def list_runs(
        self,
        workflow: str | None = None,
        branch: str | None = None,
        status: str = "failure",
        limit: int = 10,
    ) -> list[RunInfo]:
        """List runs matching criteria."""
        ...

    def download_artifacts(self, run_id: str, output_dir: Path) -> Path:
        """Download and extract run artifacts."""
        ...

    def fetch_failed_logs(self, run_id: str) -> str:
        """Fetch logs from failed jobs."""
        ...
```

#### Strategy Pattern (remote.py)
```python
from abc import ABC, abstractmethod

class TriageBundleStrategy(ABC):
    """Abstract strategy for generating triage bundles."""

    @abstractmethod
    def generate(self, run_id: str, output_dir: Path) -> TriageBundle:
        """Generate a triage bundle from the given source."""
        ...

class RemoteRunStrategy(TriageBundleStrategy):
    """Generate bundle from GitHub Actions run."""

    def __init__(self, github_client: GitHubRunClient):
        self.client = github_client

    def generate(self, run_id: str, output_dir: Path) -> TriageBundle:
        artifacts = self.client.download_artifacts(run_id, output_dir)
        report = self._find_report(artifacts)
        return self._build_bundle(report, output_dir)

class LocalArtifactsStrategy(TriageBundleStrategy):
    """Generate bundle from local artifacts directory."""

    def generate(self, artifacts_dir: Path, output_dir: Path) -> TriageBundle:
        report = self._find_report(artifacts_dir)
        return self._build_bundle(report, output_dir)

class LogFallbackStrategy(TriageBundleStrategy):
    """Generate bundle from GitHub logs when no report.json exists."""

    def generate(self, run_id: str, output_dir: Path) -> TriageBundle:
        logs = self.client.fetch_failed_logs(run_id)
        failures = self._parse_log_failures(logs)
        return self._build_bundle_from_failures(failures, output_dir)
```

#### Composition (verification.py)
```python
@dataclass
class ToolVerificationResult:
    """Result of tool verification."""
    verified: bool
    drift: list[ToolIssue]      # Configured but didn't run
    no_proof: list[ToolIssue]   # Ran but no metrics/artifacts
    failures: list[ToolIssue]   # Ran but failed
    passed: list[str]           # Ran, succeeded, has proof
    skipped: list[str]          # Not configured

    @property
    def summary(self) -> str:
        """Human-readable summary."""
        ...

    def to_problems(self) -> list[dict[str, Any]]:
        """Convert to CommandResult problems format."""
        ...

class ToolVerifier:
    """Verify that configured tools actually ran with proof."""

    def __init__(self, report_path: Path, reports_dir: Path | None = None):
        self.report_path = report_path
        self.reports_dir = reports_dir

    def verify(self) -> ToolVerificationResult:
        """Run verification and return result."""
        ...
```

### 3. Testing Strategy

#### Unit Tests (per module)
```python
# tests/test_triage_github.py
class TestGitHubRunClient:
    """Unit tests for GitHub client."""

    def test_fetch_run_info_success(self, mocker):
        """Test successful run info fetch."""
        ...

    def test_list_runs_with_filters(self, mocker):
        """Test run listing with workflow/branch filters."""
        ...

# tests/test_triage_verification.py
class TestToolVerifier:
    """Unit tests for tool verification."""

    @pytest.mark.parametrize("scenario,expected", [
        ({"configured": True, "ran": True, "success": True}, "passed"),
        ({"configured": True, "ran": False, "success": False}, "drift"),
        ({"configured": True, "ran": True, "success": False}, "failed"),
    ])
    def test_verify_tool_scenarios(self, scenario, expected, tmp_path):
        """Parameterized test for all tool states."""
        ...
```

#### Property-Based Tests (hypothesis)
```python
# tests/test_triage_properties.py
from hypothesis import given, strategies as st

class TestTriageProperties:
    """Property-based tests for triage invariants."""

    @given(st.lists(st.sampled_from(["passed", "failed", "skipped"]), min_size=1))
    def test_tool_counts_sum_to_total(self, statuses):
        """Property: sum of all status counts equals total tools."""
        ...

    @given(st.dictionaries(
        st.text(min_size=1),
        st.booleans(),
        min_size=1,
    ))
    def test_verification_handles_any_tool_config(self, tools_configured):
        """Property: verification never crashes for any tool config."""
        ...
```

#### Integration Tests
```python
# tests/test_triage_integration.py
class TestTriageCommandIntegration:
    """Integration tests for full triage flows."""

    def test_triage_latest_run(self, mocker):
        """Test --latest flag end-to-end."""
        ...

    def test_triage_multi_mode(self, tmp_path):
        """Test --multi --reports-dir end-to-end."""
        ...
```

### 4. Migration Strategy

**Phase 1** ✅ Complete (commit `4156a06`):
- [x] Create `cihub/commands/triage/` package
- [x] Extract `types.py` (constants, severity maps)
- [x] Extract `github.py` with `GitHubRunClient`
- [x] Extract `artifacts.py` (artifact finding)
- [x] Extract `log_parser.py` (failure parsing)
- [x] Update imports in `__init__.py`

**Phase 2** ✅ Complete (commit `3a37c45`):
- [x] Extract `verification.py` with `ToolVerifier`
- [x] Extract `output.py` (formatting)

**Phase 3** ✅ Complete (commit `3a37c45`):
- [x] Extract `remote.py` with strategy pattern
- [x] Extract `watch.py` (watch mode)
- [x] Refactor `triage_cmd.py` to use imports (1502→558 lines)

**Phase 4** ✅ Complete:
- [x] `__init__.py` at 133 lines (target was <300)
- [x] Add hypothesis tests (10 property-based tests in `test_triage_properties.py`)
- [x] Add integration tests (10 tests in `test_triage_integration.py`)

### 5. Backward Compatibility

All public imports remain unchanged:
```python
from cihub.commands.triage import cmd_triage  # Still works
```

## Consequences

### Positive

- **Testable**: Each module can be tested in isolation
- **Extensible**: Add new strategies without modifying existing code
- **Maintainable**: ~150-200 lines per file instead of 1452
- **Type-safe**: Dataclasses with proper type hints
- **Property-tested**: Hypothesis tests catch edge cases

### Negative

- **More files**: 8 files instead of 1
- **Initial effort**: Migration takes multiple commits
- **Learning curve**: Developers need to know which module to edit

## Related ADRs

- ADR-0025: CLI Modular Restructure (general pattern)
- ADR-0041: Language Strategy Pattern (strategy example)
- ADR-0042: CommandResult Pattern (output format)
- ADR-0043: Triage Service Modularization (service layer)

## Files Changed

```
cihub/commands/triage/
    __init__.py       # NEW
    types.py          # NEW
    github.py         # NEW
    artifacts.py      # NEW
    log_parser.py     # NEW
    remote.py         # NEW
    verification.py   # NEW
    output.py         # NEW
    watch.py          # NEW

cihub/commands/triage.py  # DELETE after migration

tests/
    test_triage_github.py        # NEW
    test_triage_verification.py  # NEW
    test_triage_properties.py    # NEW (hypothesis)
    test_triage_integration.py   # NEW
```
