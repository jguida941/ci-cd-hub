# ADR Index

Store Architecture Decision Records here (MADR style).

Existing:
- [ADR-0001: Central vs. Distributed Execution](0001-central-vs-distributed.md)
- [ADR-0002: Config Precedence Hierarchy](0002-config-precedence.md)
- [ADR-0003: Dispatch and Orchestration](0003-dispatch-orchestration.md)
- [ADR-0004: Aggregation and Reporting](0004-aggregation-reporting.md)
- [ADR-0005: Dashboard Approach](0005-dashboard-approach.md)
- [ADR-0006: Quality Gates and Thresholds](0006-quality-gates-thresholds.md)
- [ADR-0007: Templates and Profiles Strategy](0007-templates-and-profiles-strategy.md)
- [ADR-0008: Hub Fixtures Strategy](0008-hub-fixtures-strategy.md)
- [ADR-0009: Monorepo Support via repo.subdir](0009-monorepo-support.md)
- [ADR-0010: Dispatch Token and Skip Flag](0010-dispatch-token-and-skip.md)
- [ADR-0011: Dispatchable Workflow Requirement](0011-dispatchable-workflow-requirement.md)
- [ADR-0012: Kyverno Policies](0012-kyverno-policies.md)
- [ADR-0013: Dispatch Workflow Templates](0013-dispatch-workflow-templates.md) *(Superseded by ADR-0014)*
- [ADR-0014: Reusable Workflow Migration](0014-reusable-workflow-migration.md)
- [ADR-0015: Workflow Versioning & Release Policy](0015-workflow-versioning-release-policy.md)
- [ADR-0016: Mutation Testing Policy](0016-mutation-testing-policy.md)
- [ADR-0017: Scanner Tool Defaults](0017-scanner-tool-defaults.md)
- [ADR-0018: Fixtures & Testing Strategy](0018-fixtures-testing-strategy.md)
- [ADR-0019: Report Validation Policy](0019-report-validation-policy.md)
- [ADR-0020: Schema Backward Compatibility](0020-schema-backward-compatibility.md)
- [ADR-0021: Java POM Compatibility and CLI Enforcement](0021-java-pom-compatibility.md)
- [ADR-0022: Summary Verification Against Reports](0022-summary-verification.md)
- [ADR-0023: Deterministic Correlation IDs](0023-deterministic-correlation.md)
- [ADR-0024: Workflow Dispatch Input Limit](0024-workflow-dispatch-input-limit.md)
- [ADR-0025: CLI Modular Restructure](0025-cli-modular-restructure.md)
- [ADR-0026: Repo-Side Execution Guardrails](0026-repo-side-execution-guardrails.md)
- [ADR-0027: Hub Production CI Policy](0027-hub-production-ci-policy.md)
- [ADR-0028: Boolean Config Type Coercion](0028-boolean-config-type-coercion.md)
- [ADR-0029: CLI Exit Code Registry](0029-cli-exit-codes.md)
- [ADR-0031: CLI-Driven Workflow Execution (Thin Workflows)](0031-cli-driven-workflow-execution.md)
- [ADR-0032: PyQt6 GUI Wrapper for Full Automation](0032-pyqt6-cli-wrapper-full-automation.md)
- [ADR-0033: CLI Distribution and Automation Enhancements](0033-cli-distribution-and-automation.md)
- [ADR-0034: Repo Template Includes Both Language Sections](0034-repo-template-dual-language.md)
- [ADR-0035: Registry, Triage, and LLM Bundle](0035-registry-triage-llm-bundle.md)
- [ADR-0036: Service Layer APIs for GUI Integration](0036-service-layer-gui-adapter.md)
- [ADR-0037: Shorthand Enabled Sections + Threshold Profiles](0037-shorthand-enabled-sections-and-threshold-profiles.md)
- [ADR-0038: GateSpec Registry (Single Source of Truth)](0038-gatespec-registry.md)
- [ADR-0039: Require Run or Fail Policy](0039-require-run-or-fail-policy.md)
- [ADR-0040: Virtual Tools Pattern (Hypothesis, jqwik)](0040-virtual-tools-pattern.md)
- [ADR-0041: Language Strategy Pattern](0041-language-strategy-pattern.md)
- [ADR-0042: CommandResult Pattern for CLI Output](0042-command-result-pattern.md)
- [ADR-0043: Triage Service Modularization](0043-triage-service-modularization.md)
- [ADR-0044: Archive Extraction Security Hardening](0044-archive-extraction-security.md)
- [ADR-0045: Subprocess Timeout Policy](0045-subprocess-timeout-policy.md)
- [ADR-0046: OutputRenderer Pattern](0046-output-renderer-pattern.md)
- [ADR-0047: Config Validation Order](0047-config-validation-order.md)
- [ADR-0048: Documentation Automation Strategy](0048-documentation-automation-strategy.md)
- [ADR-0049: Hub Operational Settings](0049-hub-operational-settings.md)
- [ADR-0050: Triage Command Modularization](0050-triage-command-modularization.md)
- [ADR-0051: Wizard Profile-First Design](0051-wizard-profile-first-design.md)
- [ADR-0052: fail_on_* Flag Normalization](0052-fail-on-flag-normalization.md)
- [ADR-0053: Schema-Derived Defaults and Fallbacks](0053-schema-derived-defaults.md)
- [ADR-0054: Hub CI Threshold Overrides](0054-hub-ci-threshold-overrides.md)
- [ADR-0055: CLI Workflow Dispatch Watch + Wizard Wrapper](0055-cli-dispatch-watch.md)
- [ADR-0056: Docs Audit Inventory and Guide Command Validation](0056-docs-audit-inventory-and-guide-command-validation.md)
- [ADR-0057: Test Metrics Automation via hub-ci](0057-test-metrics-automation-via-hub-ci.md)
- [ADR-0058: Python CLI AI Enhancement Module](0058-python-cli-ai-enhancement.md)

Template starter:
```markdown
# ADR-XXXX: Title
Status: proposed | accepted | rejected | superseded
Date: YYYY-MM-DD

Context
Decision
Consequences (positive/negative)
Alternatives considered
```
