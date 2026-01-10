# Phase 5A: Services Layer Contract

> **WARNING: SUPERSEDED:** This services layer design is archived. The services layer was implemented; see `docs/development/active/CLEAN_CODE.md` for ongoing architecture work.
>
> **Status:** Archived (Implemented)

## Goal
Create `cihub/services/` with pure Python APIs returning dataclasses. CLI calls services, formats output.

## Types (`cihub/services/types.py`)

```python
@dataclass
class ServiceResult:
 """Not frozen to allow inheritance."""
 success: bool
 errors: list[str] = field(default_factory=list)
 warnings: list[str] = field(default_factory=list)

@dataclass
class RepoEntry:
 """Mutable - built incrementally from config loading."""
 config_basename: str
 name: str
 owner: str
 language: str
 branch: str
 subdir: str = ""
 subdir_safe: str = "" # subdir with / → -
 run_group: str = "full"
 dispatch_enabled: bool = True
 dispatch_workflow: str = "hub-ci.yml"
 tools: dict[str, bool] # run_* flags
 thresholds: dict[str, int | float | None]
 java_version: str | None = None
 python_version: str | None = None
 build_tool: str | None = None
 retention_days: int | None = None
 write_github_summary: bool = True

 @property
 def full(self) -> str:
 """owner/name"""

 def to_matrix_entry(self) -> dict[str, Any]:
 """Flattens tools/thresholds for GitHub Actions."""
```

## Discovery Service (`cihub/services/discovery.py`)

```python
@dataclass
class DiscoveryFilters:
 run_groups: list[str] = field(default_factory=list)
 repos: list[str] = field(default_factory=list)

@dataclass
class DiscoveryResult(ServiceResult):
 entries: list[RepoEntry] = field(default_factory=list)

 @property
 def count(self) -> int: ...
 def to_matrix(self) -> dict[str, Any]: ...

def discover_repositories(
 hub_root: Path,
 filters: DiscoveryFilters | None = None,
) -> DiscoveryResult:
 """Wraps existing load_config + generate_workflow_inputs.

 Captures loader stderr as warnings (no prints to terminal).
 """
```

## Design Notes

- **Not frozen**: Dataclasses are mutable to simplify construction
- **No prints in services**: Loader warnings captured as `result.warnings`
- **CLI adapter**: Formats `DiscoveryResult` for terminal output
- **GUI adapter**: Same service, different presentation
