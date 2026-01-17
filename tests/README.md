# Tests

> **Auto-generated** - Do not edit manually. Run `python scripts/generate_test_readme.py` to regenerate.
>
> Last updated: 2026-01-17 09:36:28

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 3188 |
| Test Files | 155 |
| Overall Coverage | 75.4% |

## Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| Unit | 2931 | Fast, isolated tests |
| Integration | 172 | Tests with external dependencies |
| E2E | 32 | End-to-end workflow tests |
| Property | 53 | Hypothesis property-based tests |
| Contract | 0 | API/schema contract tests |

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cihub --cov-report=html

# Run specific category
pytest tests/unit/
pytest tests/integration/

# Run fast tests only (exclude slow)
pytest -m "not slow"

# Run mutation testing
mutmut run
```

## Coverage Targets

Coverage targets are defined in `config/defaults.yaml` under the `thresholds` section:

```yaml
thresholds:
  coverage_min: 70
  mutation_score_min: 70
```

To view or modify thresholds:

```bash
cihub hub-ci thresholds show
cihub hub-ci thresholds set coverage_min 80
```

## Adding New Tests

1. Create test file in appropriate category directory
2. Follow naming convention: `test_<module>.py`
3. Add TEST-METRICS block to track coverage
4. Run `python scripts/check_test_drift.py` to verify compliance

## Coverage by Module

| Module | Coverage | Lines |
|--------|----------|-------|
| `__init__.py` | 100.0% | 2 |
| `aggregation.py` | 100.0% | 4 |
| `badges.py` | 100.0% | 20 |
| `ci_config.py` | 100.0% | 26 |
| `ci_report.py` | 100.0% | 10 |
| `ci_runner.py` | 100.0% | 4 |
| `cli.py` | 73.3% | 187 |
| `cli_parsers/__init__.py` | 100.0% | 1 |
| `cli_parsers/adr.py` | 100.0% | 21 |
| `cli_parsers/builder.py` | 94.1% | 17 |
| `cli_parsers/common.py` | 100.0% | 33 |
| `cli_parsers/config.py` | 100.0% | 45 |
| `cli_parsers/core.py` | 100.0% | 132 |
| `cli_parsers/discover.py` | 100.0% | 14 |
| `cli_parsers/dispatch.py` | 100.0% | 50 |
| `cli_parsers/docs.py` | 100.0% | 46 |
| `cli_parsers/fix.py` | 100.0% | 15 |
| `cli_parsers/gradle.py` | 100.0% | 11 |
| `cli_parsers/hub.py` | 100.0% | 32 |
| `cli_parsers/hub_ci/__init__.py` | 100.0% | 26 |
| `cli_parsers/hub_ci/badges.py` | 100.0% | 24 |
| `cli_parsers/hub_ci/java_tools.py` | 100.0% | 27 |
| `cli_parsers/hub_ci/python_tools.py` | 100.0% | 39 |
| `cli_parsers/hub_ci/release.py` | 100.0% | 86 |
| `cli_parsers/hub_ci/security.py` | 100.0% | 45 |
| `cli_parsers/hub_ci/smoke.py` | 100.0% | 23 |
| `cli_parsers/hub_ci/test_metrics.py` | 100.0% | 14 |
| `cli_parsers/hub_ci/thresholds.py` | 100.0% | 9 |
| `cli_parsers/hub_ci/validation.py` | 100.0% | 50 |
| `cli_parsers/pom.py` | 100.0% | 15 |
| `cli_parsers/profile_cmd.py` | 100.0% | 44 |
| `cli_parsers/registry.py` | 100.0% | 30 |
| `cli_parsers/registry_cmd.py` | 100.0% | 55 |
| `cli_parsers/repo_cmd.py` | 100.0% | 45 |
| `cli_parsers/repo_setup.py` | 100.0% | 63 |
| `cli_parsers/report.py` | 100.0% | 131 |
| `cli_parsers/secrets.py` | 100.0% | 19 |
| `cli_parsers/templates.py` | 100.0% | 19 |
| `cli_parsers/threshold_cmd.py` | 100.0% | 41 |
| `cli_parsers/tool_cmd.py` | 100.0% | 48 |
| `cli_parsers/triage.py` | 100.0% | 29 |
| `cli_parsers/types.py` | 100.0% | 48 |
| `commands/__init__.py` | 100.0% | 0 |
| `commands/adr.py` | 96.3% | 161 |
| `commands/ai_loop.py` | 78.7% | 47 |
| `commands/ai_loop_analysis.py` | 69.8% | 86 |
| `commands/ai_loop_artifacts.py` | 44.7% | 85 |
| `commands/ai_loop_ci.py` | 95.9% | 49 |
| `commands/ai_loop_contracts.py` | 18.8% | 48 |
| `commands/ai_loop_guardrails.py` | 34.4% | 96 |
| `commands/ai_loop_local.py` | 79.6% | 103 |
| `commands/ai_loop_remote.py` | 11.0% | 227 |
| `commands/ai_loop_results.py` | 90.0% | 20 |
| `commands/ai_loop_review.py` | 34.8% | 23 |
| `commands/ai_loop_session.py` | 87.0% | 54 |
| `commands/ai_loop_settings.py` | 73.2% | 41 |
| `commands/ai_loop_types.py` | 100.0% | 81 |
| `commands/check.py` | 60.6% | 203 |
| `commands/ci.py` | 94.9% | 98 |
| `commands/config_cmd.py` | 77.3% | 141 |
| `commands/config_outputs.py` | 96.9% | 98 |
| `commands/detect.py` | 100.0% | 20 |
| `commands/discover.py` | 89.1% | 55 |
| `commands/dispatch.py` | 56.4% | 287 |
| `commands/docs/__init__.py` | 90.2% | 51 |
| `commands/docs/generate.py` | 88.3% | 291 |
| `commands/docs/links.py` | 66.2% | 136 |
| `commands/docs_audit/__init__.py` | 90.9% | 66 |
| `commands/docs_audit/adr.py` | 89.2% | 65 |
| `commands/docs_audit/consistency.py` | 86.8% | 317 |
| `commands/docs_audit/guides.py` | 95.1% | 122 |
| `commands/docs_audit/headers.py` | 91.2% | 113 |
| `commands/docs_audit/inventory.py` | 87.2% | 47 |
| `commands/docs_audit/lifecycle.py` | 88.6% | 158 |
| `commands/docs_audit/output.py` | 11.0% | 82 |
| `commands/docs_audit/references.py` | 41.4% | 87 |
| `commands/docs_audit/types.py` | 100.0% | 119 |
| `commands/docs_stale/__init__.py` | 33.0% | 91 |
| `commands/docs_stale/comparison.py` | 90.3% | 31 |
| `commands/docs_stale/extraction.py` | 88.6% | 132 |
| `commands/docs_stale/git.py` | 20.7% | 111 |
| `commands/docs_stale/output.py` | 79.6% | 108 |
| `commands/docs_stale/types.py` | 100.0% | 50 |
| `commands/fix.py` | 96.5% | 170 |
| `commands/gradle.py` | 98.8% | 80 |
| `commands/hub_ci/__init__.py` | 66.8% | 244 |
| `commands/hub_ci/badges.py` | 59.2% | 130 |
| `commands/hub_ci/java_tools.py` | 46.0% | 137 |
| `commands/hub_ci/python_tools.py` | 97.5% | 240 |
| `commands/hub_ci/release.py` | 84.2% | 564 |
| `commands/hub_ci/router.py` | 100.0% | 23 |
| `commands/hub_ci/security.py` | 93.0% | 215 |
| `commands/hub_ci/smoke.py` | 43.3% | 97 |
| `commands/hub_ci/test_metrics.py` | 69.5% | 105 |
| `commands/hub_ci/thresholds.py` | 20.4% | 54 |
| `commands/hub_ci/validation.py` | 43.2% | 264 |
| `commands/hub_config.py` | 0.0% | 111 |
| `commands/init.py` | 88.6% | 140 |
| `commands/new.py` | 83.5% | 97 |
| `commands/pom.py` | 87.0% | 154 |
| `commands/preflight.py` | 91.8% | 73 |
| `commands/profile_cmd.py` | 58.0% | 383 |
| `commands/registry/__init__.py` | 100.0% | 17 |
| `commands/registry/_utils.py` | 72.7% | 22 |
| `commands/registry/io.py` | 90.3% | 113 |
| `commands/registry/modify.py` | 71.0% | 131 |
| `commands/registry/query.py` | 87.5% | 32 |
| `commands/registry/sync.py` | 84.3% | 140 |
| `commands/registry_cmd.py` | 100.0% | 3 |
| `commands/repo_cmd.py` | 46.1% | 280 |
| `commands/report/__init__.py` | 57.9% | 95 |
| `commands/report/aggregate.py` | 20.3% | 59 |
| `commands/report/build.py` | 88.8% | 98 |
| `commands/report/dashboard.py` | 88.5% | 113 |
| `commands/report/helpers.py` | 89.7% | 58 |
| `commands/report/outputs.py` | 100.0% | 29 |
| `commands/report/summary.py` | 100.0% | 55 |
| `commands/report/validate.py` | 70.6% | 51 |
| `commands/run.py` | 100.0% | 56 |
| `commands/scaffold.py` | 81.4% | 97 |
| `commands/schema_sync.py` | 80.4% | 97 |
| `commands/secrets.py` | 84.3% | 172 |
| `commands/setup.py` | 56.4% | 202 |
| `commands/smoke.py` | 78.5% | 191 |
| `commands/templates.py` | 92.7% | 137 |
| `commands/threshold_cmd.py` | 38.5% | 423 |
| `commands/tool_cmd.py` | 54.5% | 690 |
| `commands/triage/__init__.py` | 100.0% | 20 |
| `commands/triage/artifacts.py` | 50.0% | 18 |
| `commands/triage/github.py` | 94.1% | 118 |
| `commands/triage/log_parser.py` | 53.9% | 180 |
| `commands/triage/output.py` | 75.0% | 32 |
| `commands/triage/remote.py` | 26.8% | 112 |
| `commands/triage/types.py` | 100.0% | 38 |
| `commands/triage/verification.py` | 91.9% | 123 |
| `commands/triage/watch.py` | 22.0% | 59 |
| `commands/triage_cmd.py` | 68.9% | 193 |
| `commands/update.py` | 85.0% | 107 |
| `commands/validate.py` | 98.2% | 55 |
| `commands/verify.py` | 51.2% | 244 |
| `config/__init__.py` | 100.0% | 7 |
| `config/fallbacks.py` | 100.0% | 3 |
| `config/io.py` | 100.0% | 66 |
| `config/loader/__init__.py` | 100.0% | 6 |
| `config/loader/core.py` | 74.8% | 107 |
| `config/loader/inputs.py` | 98.9% | 88 |
| `config/merge.py` | 100.0% | 27 |
| `config/normalize.py` | 92.9% | 126 |
| `config/paths.py` | 100.0% | 35 |
| `config/schema.py` | 97.7% | 44 |
| `config/schema_extract.py` | 92.3% | 168 |
| `core/__init__.py` | 100.0% | 4 |
| `core/aggregation/__init__.py` | 100.0% | 8 |
| `core/aggregation/artifacts.py` | 14.8% | 54 |
| `core/aggregation/github_api.py` | 17.1% | 70 |
| `core/aggregation/metrics.py` | 100.0% | 28 |
| `core/aggregation/render.py` | 79.3% | 150 |
| `core/aggregation/runner.py` | 50.2% | 247 |
| `core/aggregation/status.py` | 79.4% | 131 |
| `core/badges.py` | 93.5% | 169 |
| `core/ci_report.py` | 98.9% | 186 |
| `core/ci_runner/__init__.py` | 100.0% | 10 |
| `core/ci_runner/base.py` | 100.0% | 3 |
| `core/ci_runner/docker_tools.py` | 39.8% | 93 |
| `core/ci_runner/java_tools.py` | 66.3% | 101 |
| `core/ci_runner/parsers.py` | 86.1% | 144 |
| `core/ci_runner/python_tools.py` | 87.3% | 166 |
| `core/ci_runner/sbom_tools.py` | 88.5% | 26 |
| `core/ci_runner/security_tools.py` | 12.5% | 48 |
| `core/ci_runner/shared.py` | 62.1% | 95 |
| `core/correlation.py` | 91.9% | 86 |
| `core/gate_specs.py` | 97.5% | 81 |
| `core/languages/__init__.py` | 100.0% | 3 |
| `core/languages/base.py` | 80.8% | 52 |
| `core/languages/java.py` | 53.8% | 186 |
| `core/languages/python.py` | 89.3% | 56 |
| `core/languages/registry.py` | 87.2% | 47 |
| `core/reporting.py` | 80.0% | 444 |
| `correlation.py` | 100.0% | 4 |
| `diagnostics/__init__.py` | 100.0% | 3 |
| `diagnostics/collectors/__init__.py` | 100.0% | 0 |
| `diagnostics/models.py` | 100.0% | 44 |
| `diagnostics/renderer.py` | 97.2% | 36 |
| `exit_codes.py` | 100.0% | 7 |
| `output/__init__.py` | 100.0% | 3 |
| `output/ai_formatters.py` | 100.0% | 13 |
| `output/renderers.py` | 91.2% | 148 |
| `reporting.py` | 100.0% | 30 |
| `services/__init__.py` | 100.0% | 10 |
| `services/aggregation.py` | 100.0% | 49 |
| `services/ai/__init__.py` | 100.0% | 2 |
| `services/ai/patterns.py` | 97.5% | 40 |
| `services/ci.py` | 100.0% | 3 |
| `services/ci_engine/__init__.py` | 87.2% | 156 |
| `services/ci_engine/gates.py` | 84.3% | 236 |
| `services/ci_engine/helpers.py` | 95.5% | 111 |
| `services/ci_engine/io.py` | 84.2% | 38 |
| `services/ci_engine/java_tools.py` | 49.5% | 111 |
| `services/ci_engine/notifications.py` | 97.1% | 69 |
| `services/ci_engine/python_tools.py` | 70.5% | 156 |
| `services/ci_engine/validation.py` | 84.2% | 19 |
| `services/configuration.py` | 25.0% | 204 |
| `services/detection.py` | 96.2% | 26 |
| `services/discovery.py` | 85.0% | 100 |
| `services/registry/__init__.py` | 100.0% | 9 |
| `services/registry/_paths.py` | 84.6% | 13 |
| `services/registry/diff.py` | 87.6% | 291 |
| `services/registry/io.py` | 95.5% | 22 |
| `services/registry/normalize.py` | 95.3% | 43 |
| `services/registry/query.py` | 63.6% | 121 |
| `services/registry/sync.py` | 85.4% | 288 |
| `services/registry/thresholds.py` | 84.3% | 70 |
| `services/registry_service.py` | 100.0% | 3 |
| `services/repo_config.py` | 89.5% | 57 |
| `services/report_summary.py` | 100.0% | 24 |
| `services/report_validator/__init__.py` | 100.0% | 9 |
| `services/report_validator/artifact.py` | 90.9% | 22 |
| `services/report_validator/content.py` | 90.2% | 254 |
| `services/report_validator/schema.py` | 100.0% | 20 |
| `services/report_validator/types.py` | 100.0% | 20 |
| `services/templates.py` | 96.7% | 61 |
| `services/triage/__init__.py` | 100.0% | 5 |
| `services/triage/detection.py` | 99.2% | 119 |
| `services/triage/evidence.py` | 97.5% | 160 |
| `services/triage/types.py` | 100.0% | 50 |
| `services/triage_service.py` | 93.2% | 205 |
| `services/types.py` | 100.0% | 63 |
| `tools/__init__.py` | 100.0% | 3 |
| `tools/registry.py` | 92.2% | 129 |
| `types.py` | 98.1% | 53 |
| `utils/__init__.py` | 100.0% | 9 |
| `utils/debug.py` | 100.0% | 19 |
| `utils/env.py` | 100.0% | 52 |
| `utils/env_registry.py` | 100.0% | 19 |
| `utils/exec_utils.py` | 96.9% | 32 |
| `utils/filesystem.py` | 87.8% | 41 |
| `utils/fs.py` | 100.0% | 10 |
| `utils/git.py` | 97.8% | 46 |
| `utils/github.py` | 31.8% | 88 |
| `utils/github_api.py` | 52.2% | 46 |
| `utils/github_context.py` | 98.2% | 110 |
| `utils/java_gradle.py` | 21.1% | 199 |
| `utils/java_pom/__init__.py` | 100.0% | 5 |
| `utils/java_pom/apply.py` | 91.8% | 97 |
| `utils/java_pom/parse.py` | 96.8% | 124 |
| `utils/java_pom/rules.py` | 87.5% | 96 |
| `utils/net.py` | 100.0% | 8 |
| `utils/paths.py` | 100.0% | 20 |
| `utils/progress.py` | 100.0% | 6 |
| `utils/project.py` | 100.0% | 41 |
| `utils/validation.py` | 100.0% | 15 |
| `wizard/__init__.py` | 77.8% | 9 |
| `wizard/validators.py` | 100.0% | 25 |
