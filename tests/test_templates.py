"""
Tests for template and profile validation.

Validates that:
1. All hub config templates pass schema validation
2. All profiles, when merged with a minimal repo config, produce valid configs
3. Templates don't reference stale repo names
"""

import argparse
import re
import sys
from pathlib import Path
from unittest import mock

import pytest

from cihub.config.io import load_yaml_file
from cihub.config.loader import ConfigValidationError, load_config
from cihub.config.merge import deep_merge

# Allow importing scripts as modules (for validate_config which is not yet migrated)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.utils.paths import hub_root  # noqa: E402
from scripts.validate_config import validate_config  # noqa: E402

TEMPLATES_DIR = hub_root() / "templates"
PROFILES_DIR = TEMPLATES_DIR / "profiles"
HUB_TEMPLATES_DIR = TEMPLATES_DIR / "hub" / "config" / "repos"
SCHEMA_PATH = hub_root() / "schema" / "ci-hub-config.schema.json"


def load_schema():
    """Load the JSON schema for config validation."""
    import json

    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


# Minimal valid repo configs for testing profile merges
MINIMAL_JAVA_REPO = {
    "repo": {
        "owner": "test-owner",
        "name": "test-repo",
        "language": "java",
    },
    "language": "java",
}

MINIMAL_PYTHON_REPO = {
    "repo": {
        "owner": "test-owner",
        "name": "test-repo",
        "language": "python",
    },
    "language": "python",
}


class TestHubConfigTemplates:
    """Test hub-side config templates."""

    def get_hub_templates(self):
        """Get all hub config template files."""
        if not HUB_TEMPLATES_DIR.exists():
            return []
        return list(HUB_TEMPLATES_DIR.glob("*.yaml"))

    def test_hub_templates_exist(self):
        """Ensure hub templates directory has templates."""
        templates = self.get_hub_templates()
        assert len(templates) > 0, "No hub config templates found"

    @pytest.mark.parametrize(
        "template_path",
        [pytest.param(p, id=p.name) for p in (HUB_TEMPLATES_DIR.glob("*.yaml") if HUB_TEMPLATES_DIR.exists() else [])],
    )
    def test_hub_template_is_valid_yaml(self, template_path):
        """Each hub template should be valid YAML."""
        data = load_yaml_file(template_path)
        assert isinstance(data, dict), f"{template_path.name} should be a mapping"

    @pytest.mark.parametrize(
        "template_path",
        [pytest.param(p, id=p.name) for p in (HUB_TEMPLATES_DIR.glob("*.yaml") if HUB_TEMPLATES_DIR.exists() else [])],
    )
    def test_hub_template_has_required_fields(self, template_path):
        """Hub templates should have repo section with required fields."""
        data = load_yaml_file(template_path)

        # Templates might be partial (for merging), but full templates need repo
        if "repo" in data:
            repo = data["repo"]
            assert "owner" in repo or "name" in repo, f"{template_path.name} repo section should have owner or name"


class TestProfileTemplates:
    """Test profile templates."""

    def get_python_profiles(self):
        """Get all Python profile files."""
        if not PROFILES_DIR.exists():
            return []
        return list(PROFILES_DIR.glob("python-*.yaml"))

    def get_java_profiles(self):
        """Get all Java profile files."""
        if not PROFILES_DIR.exists():
            return []
        return list(PROFILES_DIR.glob("java-*.yaml"))

    def test_profiles_exist(self):
        """Ensure profiles directory has profiles."""
        python_profiles = self.get_python_profiles()
        java_profiles = self.get_java_profiles()
        assert len(python_profiles) > 0, "No Python profiles found"
        assert len(java_profiles) > 0, "No Java profiles found"

    @pytest.mark.parametrize(
        "profile_path",
        [pytest.param(p, id=p.name) for p in (PROFILES_DIR.glob("*.yaml") if PROFILES_DIR.exists() else [])],
    )
    def test_profile_is_valid_yaml(self, profile_path):
        """Each profile should be valid YAML."""
        data = load_yaml_file(profile_path)
        assert isinstance(data, dict), f"{profile_path.name} should be a mapping"

    @pytest.mark.parametrize(
        "profile_path",
        [pytest.param(p, id=p.name) for p in (PROFILES_DIR.glob("python-*.yaml") if PROFILES_DIR.exists() else [])],
    )
    def test_python_profile_merged_is_valid(self, profile_path):
        """Python profile + minimal repo config should pass schema validation."""
        profile_data = load_yaml_file(profile_path)
        merged = deep_merge(profile_data, MINIMAL_PYTHON_REPO)

        schema = load_schema()
        errors = validate_config(merged, schema)

        assert not errors, f"{profile_path.name} merged with minimal repo has errors: {errors}"

    @pytest.mark.parametrize(
        "profile_path",
        [pytest.param(p, id=p.name) for p in (PROFILES_DIR.glob("java-*.yaml") if PROFILES_DIR.exists() else [])],
    )
    def test_java_profile_merged_is_valid(self, profile_path):
        """Java profile + minimal repo config should pass schema validation."""
        profile_data = load_yaml_file(profile_path)
        merged = deep_merge(profile_data, MINIMAL_JAVA_REPO)

        schema = load_schema()
        errors = validate_config(merged, schema)

        assert not errors, f"{profile_path.name} merged with minimal repo has errors: {errors}"


class TestNoStaleReferences:
    """Test that templates don't reference old/stale names."""

    STALE_PATTERNS = [
        "ci-hub-orchestrator",  # Old repo name
        "jguida941/ci-hub-orchestrator",  # Old full name
    ]

    def get_all_template_files(self):
        """Get all template files (YAML and MD)."""
        files = []
        if TEMPLATES_DIR.exists():
            files.extend(TEMPLATES_DIR.rglob("*.yaml"))
            files.extend(TEMPLATES_DIR.rglob("*.yml"))
            files.extend(TEMPLATES_DIR.rglob("*.md"))
        return files

    @pytest.mark.parametrize(
        "template_path",
        [
            pytest.param(p, id=str(p.relative_to(ROOT)))
            for p in (TEMPLATES_DIR.rglob("*") if TEMPLATES_DIR.exists() else [])
            if p.is_file() and p.suffix in {".yaml", ".yml", ".md"}
        ],
    )
    def test_no_stale_repo_references(self, template_path):
        """Templates should not reference old repo names."""
        content = template_path.read_text(encoding="utf-8")

        for pattern in self.STALE_PATTERNS:
            assert pattern not in content, f"{template_path} contains stale reference: {pattern}"


class TestRepoTemplate:
    """Test the main repo template used for onboarding."""

    REPO_TEMPLATE = TEMPLATES_DIR / "repo" / ".ci-hub.yml"

    def test_repo_template_exists(self):
        """The repo-side .ci-hub.yml template should exist."""
        assert self.REPO_TEMPLATE.exists(), f"Repo template not found at {self.REPO_TEMPLATE}"

    def test_repo_template_is_valid_yaml(self):
        """Repo template should be valid YAML."""
        if not self.REPO_TEMPLATE.exists():
            pytest.skip("Repo template not found")

        data = load_yaml_file(self.REPO_TEMPLATE)
        assert isinstance(data, dict), "Repo template should be a mapping"


class TestCallerTemplates:
    """Test repo caller workflow templates."""

    JAVA_CALLER = TEMPLATES_DIR / "repo" / "hub-java-ci.yml"
    PYTHON_CALLER = TEMPLATES_DIR / "repo" / "hub-python-ci.yml"

    def test_java_caller_template_exists(self):
        """Java caller template should exist."""
        assert self.JAVA_CALLER.exists(), f"Java caller template not found at {self.JAVA_CALLER}"

    def test_python_caller_template_exists(self):
        """Python caller template should exist."""
        assert self.PYTHON_CALLER.exists(), f"Python caller template not found at {self.PYTHON_CALLER}"

    def test_java_caller_is_valid_yaml(self):
        """Java caller template should be valid YAML."""
        if not self.JAVA_CALLER.exists():
            pytest.skip("Java caller template not found")

        data = load_yaml_file(self.JAVA_CALLER)
        assert isinstance(data, dict), "Java caller should be a mapping"
        assert "on" in data or "jobs" in data, "Should look like a workflow"

    def test_python_caller_is_valid_yaml(self):
        """Python caller template should be valid YAML."""
        if not self.PYTHON_CALLER.exists():
            pytest.skip("Python caller template not found")

        data = load_yaml_file(self.PYTHON_CALLER)
        assert isinstance(data, dict), "Python caller should be a mapping"
        assert "on" in data or "jobs" in data, "Should look like a workflow"


class TestRenderCallerWorkflow:
    """Test that render_caller_workflow produces valid output matching templates."""

    @pytest.mark.parametrize(
        "language,template_file",
        [
            ("java", "hub-java-ci.yml"),
            ("python", "hub-python-ci.yml"),
        ],
    )
    def test_render_dispatch_workflow_matches_template(self, language: str, template_file: str):
        """render_dispatch_workflow for language-specific files returns template content."""
        from cihub.services.templates import render_dispatch_workflow

        rendered = render_dispatch_workflow(language, template_file)
        template_path = TEMPLATES_DIR / "repo" / template_file
        expected = template_path.read_text(encoding="utf-8")
        assert rendered == expected, f"render_dispatch_workflow({language}, {template_file}) differs from template"

    @pytest.mark.parametrize("language", ["java", "python"])
    def test_render_hub_ci_includes_header(self, language: str):
        """render_dispatch_workflow for hub-ci.yml includes generated header."""
        from cihub.services.templates import render_dispatch_workflow

        rendered = render_dispatch_workflow(language, "hub-ci.yml")
        assert rendered.startswith("# Generated by cihub init"), "hub-ci.yml should have generated header"

    @pytest.mark.parametrize("language", ["java", "python"])
    def test_render_hub_ci_replaces_workflow_name(self, language: str):
        """render_dispatch_workflow for hub-ci.yml replaces language-specific workflow name."""
        from cihub.services.templates import render_dispatch_workflow

        rendered = render_dispatch_workflow(language, "hub-ci.yml")
        # Should NOT contain the original template name
        assert f"hub-{language}-ci.yml" not in rendered, "Should replace template name with hub-ci.yml"
        # Should contain hub-ci.yml (the replacement)
        assert "hub-ci.yml" in rendered


class TestLegacyDispatchTemplates:
    """Ensure legacy dispatch templates stay archived."""

    LEGACY_DIR = TEMPLATES_DIR / "legacy"
    LEGACY_TEMPLATES = [
        LEGACY_DIR / "java-ci-dispatch.yml",
        LEGACY_DIR / "python-ci-dispatch.yml",
    ]

    def test_legacy_templates_archived(self):
        """Legacy dispatch templates should live under templates/legacy."""
        for path in self.LEGACY_TEMPLATES:
            assert path.exists(), f"Legacy template not found at {path}"

    def test_legacy_templates_not_active(self):
        """Legacy dispatch templates should not exist in active paths."""
        assert not (TEMPLATES_DIR / "java" / "java-ci-dispatch.yml").exists()
        assert not (TEMPLATES_DIR / "python" / "python-ci-dispatch.yml").exists()


class TestHubRunAllSummary:
    """Guard against summary fallbacks masking disabled tools."""

    HUB_RUN_ALL = ROOT / ".github" / "workflows" / "hub-run-all.yml"

    def test_summary_does_not_force_true(self) -> None:
        content = self.HUB_RUN_ALL.read_text(encoding="utf-8")
        assert not re.search(r"matrix\.run_[A-Za-z0-9_]+\s*\|\|", content), (
            "hub-run-all.yml should not force matrix.run_* values with '||' fallbacks"
        )


class TestActualConfigs:
    """Test that actual repo configs in config/repos/ are valid."""

    CONFIG_DIR = hub_root() / "config" / "repos"

    def get_actual_configs(self):
        """Get all actual repo config files."""
        if not self.CONFIG_DIR.exists():
            return []
        return list(self.CONFIG_DIR.glob("*.yaml"))

    def test_configs_exist(self):
        """Ensure we have actual repo configs."""
        configs = self.get_actual_configs()
        assert len(configs) > 0, "No repo configs found in config/repos/"

    @pytest.mark.parametrize(
        "config_path",
        [
            pytest.param(p, id=p.stem)
            for p in ((hub_root() / "config" / "repos").glob("*.yaml") if (hub_root() / "config" / "repos").exists() else [])
        ],
    )
    def test_actual_config_is_valid(self, config_path):
        """Each actual repo config should pass validation."""
        try:
            cfg = load_config(
                repo_name=config_path.stem,
                hub_root=hub_root(),
                exit_on_validation_error=False,
            )
            assert cfg is not None
            assert "repo" in cfg
        except ConfigValidationError as e:
            pytest.fail(f"{config_path.stem} failed validation: {e}")


# ==============================================================================
# Tests for cmd_sync_templates (cihub/commands/templates.py)
# ==============================================================================


class TestSyncTemplatesCommand:
    """Tests for the sync-templates command logic."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Import templates module and set GH_TOKEN for mocked API calls."""
        # Import module first so patches can find it
        import cihub.commands.templates  # noqa: F401

        # Set GH_TOKEN so sync-templates proceeds past token check
        monkeypatch.setenv("GH_TOKEN", "test-token-for-mocked-api")

    @pytest.fixture
    def mock_get_repo_entries(self):
        """Mock get_repo_entries to return test repos."""
        with mock.patch("cihub.commands.templates.get_repo_entries") as m:
            m.return_value = [
                {
                    "full": "owner/python-repo",
                    "language": "python",
                    "dispatch_workflow": "hub-ci.yml",
                    "default_branch": "main",
                },
                {
                    "full": "owner/java-repo",
                    "language": "java",
                    "dispatch_workflow": "hub-ci.yml",
                    "default_branch": "main",
                },
            ]
            yield m

    @pytest.fixture
    def mock_render_dispatch_workflow(self):
        """Mock render_dispatch_workflow."""
        with mock.patch("cihub.commands.templates.render_dispatch_workflow") as m:
            m.return_value = "# Generated workflow content"
            yield m

    @pytest.fixture
    def mock_fetch_remote_file(self):
        """Mock fetch_remote_file."""
        with mock.patch("cihub.commands.templates.fetch_remote_file") as m:
            yield m

    @pytest.fixture
    def mock_update_remote_file(self):
        """Mock update_remote_file."""
        with mock.patch("cihub.commands.templates.update_remote_file") as m:
            yield m

    @pytest.fixture
    def mock_delete_remote_file(self):
        """Mock delete_remote_file."""
        with mock.patch("cihub.commands.templates.delete_remote_file") as m:
            yield m

    def test_sync_no_repos(self) -> None:
        """Handle case when no repos found."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        with mock.patch("cihub.commands.templates.get_repo_entries") as m:
            m.return_value = []
            args = argparse.Namespace(
                repo=None,
                include_disabled=False,
                check=False,
                dry_run=False,
                commit_message="chore: sync templates",
                update_tag=False,
            )
            result = cmd_sync_templates(args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == 0
            assert "No repos found" in result.summary

    def test_sync_remote_up_to_date(
        self,
        mock_get_repo_entries,
        mock_render_dispatch_workflow,
        mock_fetch_remote_file,
    ) -> None:
        """Report OK when remote matches desired content."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        mock_fetch_remote_file.return_value = {"content": "# Generated workflow content"}

        args = argparse.Namespace(
            repo=None,
            include_disabled=False,
            check=False,
            dry_run=False,
            commit_message="chore: sync templates",
            update_tag=False,
        )
        result = cmd_sync_templates(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        items = result.data.get("items", [])
        assert any("[OK]" in item and "up to date" in item for item in items)

    def test_sync_check_mode_detects_drift(
        self,
        mock_get_repo_entries,
        mock_render_dispatch_workflow,
        mock_fetch_remote_file,
    ) -> None:
        """Check mode reports drift without updating."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        mock_fetch_remote_file.return_value = {"content": "# Old content"}

        args = argparse.Namespace(
            repo=None,
            include_disabled=False,
            check=True,
            dry_run=False,
            commit_message="chore: sync templates",
            update_tag=False,
        )
        result = cmd_sync_templates(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 1
        items = result.data.get("items", [])
        assert any("[FAIL]" in item and "out of date" in item for item in items)
        assert any("drift detected" in item for item in items)

    def test_sync_dry_run_mode(
        self,
        mock_get_repo_entries,
        mock_render_dispatch_workflow,
        mock_fetch_remote_file,
        mock_update_remote_file,
    ) -> None:
        """Dry run shows what would be updated without doing it."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        mock_fetch_remote_file.return_value = {"content": "# Old content"}

        args = argparse.Namespace(
            repo=None,
            include_disabled=False,
            check=False,
            dry_run=True,
            commit_message="chore: sync templates",
            update_tag=False,
        )
        result = cmd_sync_templates(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        items = result.data.get("items", [])
        assert any("Would update" in item for item in items)
        mock_update_remote_file.assert_not_called()

    def test_sync_updates_remote(
        self,
        mock_get_repo_entries,
        mock_render_dispatch_workflow,
        mock_fetch_remote_file,
        mock_update_remote_file,
    ) -> None:
        """Sync updates remote file when content differs."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        mock_fetch_remote_file.return_value = {
            "content": "# Old content",
            "sha": "abc123",
        }

        args = argparse.Namespace(
            repo=None,
            include_disabled=False,
            check=False,
            dry_run=False,
            commit_message="chore: sync templates",
            update_tag=False,
        )
        result = cmd_sync_templates(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        mock_update_remote_file.assert_called()
        items = result.data.get("items", [])
        assert any("updated" in item for item in items)

    def test_sync_specific_repo(
        self,
        mock_render_dispatch_workflow,
        mock_fetch_remote_file,
    ) -> None:
        """Sync only specific repo when --repo provided."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        with mock.patch("cihub.commands.templates.get_repo_entries") as m:
            m.return_value = [
                {
                    "full": "owner/python-repo",
                    "language": "python",
                    "dispatch_workflow": "hub-ci.yml",
                    "default_branch": "main",
                },
                {
                    "full": "owner/java-repo",
                    "language": "java",
                    "dispatch_workflow": "hub-ci.yml",
                    "default_branch": "main",
                },
            ]
            mock_fetch_remote_file.return_value = {"content": "# Generated workflow content"}

            args = argparse.Namespace(
                repo=["owner/python-repo"],
                include_disabled=False,
                check=False,
                dry_run=False,
                commit_message="chore: sync templates",
                update_tag=False,
            )
            result = cmd_sync_templates(args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == 0
            items = result.data.get("items", [])
            assert any("python-repo" in item for item in items)
            # Only python-repo should appear, not java-repo
            ok_count = sum(1 for item in items if "[OK]" in item)
            assert ok_count == 1

    def test_sync_repo_not_found(self) -> None:
        """Error when specified repo not found in configs."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        with mock.patch("cihub.commands.templates.get_repo_entries") as m:
            m.return_value = [
                {
                    "full": "owner/existing-repo",
                    "language": "python",
                    "dispatch_workflow": "hub-ci.yml",
                    "default_branch": "main",
                },
            ]
            args = argparse.Namespace(
                repo=["owner/nonexistent-repo"],
                include_disabled=False,
                check=False,
                dry_run=False,
                commit_message="chore: sync templates",
                update_tag=False,
            )
            result = cmd_sync_templates(args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == 2
            assert "not found" in result.summary.lower()

    def test_sync_render_error(
        self,
        mock_get_repo_entries,
    ) -> None:
        """Handle render error gracefully."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        with mock.patch("cihub.commands.templates.render_dispatch_workflow") as m:
            m.side_effect = ValueError("Unsupported language")
            args = argparse.Namespace(
                repo=None,
                include_disabled=False,
                check=False,
                dry_run=False,
                commit_message="chore: sync templates",
                update_tag=False,
            )
            result = cmd_sync_templates(args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == 1
            items = result.data.get("items", [])
            assert any("ERROR" in item for item in items)

    def test_sync_deletes_stale_workflows(
        self,
        mock_render_dispatch_workflow,
        mock_fetch_remote_file,
        mock_update_remote_file,
        mock_delete_remote_file,
    ) -> None:
        """Delete stale workflows after successful sync to hub-ci.yml."""
        from cihub.commands.templates import cmd_sync_templates
        from cihub.types import CommandResult

        with mock.patch("cihub.commands.templates.get_repo_entries") as m:
            m.return_value = [
                {
                    "full": "owner/repo",
                    "language": "python",
                    "dispatch_workflow": "hub-ci.yml",
                    "default_branch": "main",
                },
            ]
            # Main workflow is up to date
            # Stale workflow exists
            mock_fetch_remote_file.side_effect = [
                {"content": "# Generated workflow content"},  # hub-ci.yml
                {"sha": "stale123"},  # hub-java-ci.yml (stale)
                None,  # hub-python-ci.yml (not found)
            ]

            args = argparse.Namespace(
                repo=None,
                include_disabled=False,
                check=False,
                dry_run=False,
                commit_message="chore: sync templates",
                update_tag=False,
            )
            result = cmd_sync_templates(args)
            assert isinstance(result, CommandResult)
            assert result.exit_code == 0
            mock_delete_remote_file.assert_called_once()
            items = result.data.get("items", [])
            assert any("deleted" in item for item in items)
