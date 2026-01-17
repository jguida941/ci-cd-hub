  🔴 CRITICAL GAPS (Users Can't Do These Today)

  1. No Pre-commit Hook Integration

  - Users can't generate .pre-commit-config.yaml from their .ci-hub.yml
  - No cihub hooks generate or cihub hooks install command
  - Why it matters: Most teams want local linting before push - currently they have to manually maintain pre-commit config separately from CI config
  - Suggested: cihub hooks generate --install that creates pre-commit config matching their enabled tools (ruff, black, isort, checkstyle, etc.)

  2. No IDE Configuration Generation

  - Can't generate .vscode/settings.json or .idea/ configs from .ci-hub.yml
  - Why it matters: Developer environment should match CI to avoid "works on my machine" issues
  - Suggested: cihub ide generate --vscode / --intellij to create configs that match CI tool settings

  3. No Branch-Specific Configurations

  - Can't configure different tool sets per branch (e.g., strict on main, relaxed on feature branches)
  - Config is one-size-fits-all per repo
  - Why it matters: Teams want fast CI on PRs but full security scans on main/release branches
  - Suggested: Add branches: section to config schema with per-branch tool overrides

  4. No Scheduled/Cron Job Support in Config

  - Can't define scheduled security scans or nightly full test runs from .ci-hub.yml
  - Workflows support it, but not exposed through config
  - Why it matters: Security teams want weekly full scans without slowing down PR feedback
  - Suggested: schedules: section in config for defining cron-triggered profiles

  5. No Test Parallelization Configuration

  - Can't configure pytest -n auto or Maven surefire parallel from config
  - No way to split test suites across runners
  - Why it matters: Large test suites need parallelization to stay fast
  - Suggested: Add pytest.parallel and java.parallel_tests config options

  ---
  🟡 USABILITY GAPS (Users Can Do It, But It's Hard)

  6. No Config Diff/Compare Between Repos

  - cihub threshold compare exists but no general cihub config diff repo-a repo-b
  - Hard to see what's different between repos
  - Suggested: cihub config diff --repo repo-a --repo repo-b

  7. No Config Import from Existing CI

  - Can't import settings from existing .github/workflows/*.yml into .ci-hub.yml
  - Users migrating from custom CI have to manually translate
  - Suggested: cihub import --from .github/workflows/ci.yml

  8. No Dry-Run for All Commands

  - Some commands have --dry-run, many don't
  - Users can't preview what cihub ci will actually run
  - Suggested: cihub ci --dry-run to show tool execution plan without running

  9. No "Why Did This Fail" Explanation

  - cihub triage gives bundle but no human-readable explanation
  - cihub fix --ai exists but no cihub explain for understanding failures
  - Suggested: cihub explain --run <id> that gives plain-English failure analysis

  10. No Config Linting/Best Practices Check

  - cihub validate checks schema but not best practices
  - Doesn't warn about: disabled security tools, low thresholds, missing recommended tools
  - Suggested: cihub config lint or cihub validate --best-practices

  ---
  🟢 FLEXIBILITY GAPS (Would Extend What's Possible)

  11. No Custom Tool Arguments

  - Can enable/disable tools but can't pass custom args to underlying commands
  - Example: Can't add --ignore=E501 to ruff beyond what config allows
  - Suggested: Per-tool extra_args field: ruff: { enabled: true, extra_args: ["--ignore=E501"] }

  12. No Conditional Tool Execution

  - Can't run spotbugs only if checkstyle passes
  - Can't skip mutation if coverage is below threshold
  - Suggested: depends_on or condition fields in tool config

  13. No Custom Report Formats

  - Reports are JSON/SARIF only
  - Users may want JUnit XML, custom templates, or team-specific formats
  - Suggested: cihub report render --template custom.j2

  14. No Artifact Retention Configuration

  - reports.retention_days exists but can't configure per-artifact-type
  - May want to keep coverage reports longer than lint reports
  - Suggested: Per-tool retention settings

  15. No Matrix Testing Support

  - Can't define matrix of Python versions (3.10, 3.11, 3.12) or Java versions (17, 21)
  - Single version per repo only
  - Suggested: python.versions: [3.10, 3.11, 3.12] for matrix builds

  ---
  🔵 WIZARD GAPS (Missing Questions/Flows)

  16. No "Copy Config From Another Repo" in Wizard

  - Can't say "set up like repo-x"
  - Have to manually answer all questions
  - Suggested: Wizard option: "Use settings from existing repo?"

  17. No Quick Edit Mode

  - cihub config edit opens full wizard, can't just change one tool
  - Suggested: cihub config set --repo X python.tools.ruff.enabled=false (already exists but wizard doesn't offer quick mode)

  18. No Wizard for CI Migration

  - Wizard is for new setup only
  - No guided migration from Travis/CircleCI/Jenkins
  - Suggested: cihub migrate --from travis wizard

  19. No Profile Preview in Wizard

  - Shows profile names but not what tools are enabled
  - User has to guess what "quality" vs "compliance" means
  - Suggested: Show tool list inline during profile selection

  20. No "What Changed" Summary After Wizard

  - Wizard writes config but doesn't show diff from previous
  - Suggested: Show before/after diff at end of wizard

  ---
  🟣 MISSING TOOL INTEGRATIONS (Python/Java Specific)

  Python:

  21. No pylint support (only ruff) - some teams require pylint specifically
  22. No poetry/pdm/uv awareness - only pip-based install
  23. No sphinx docs build integration - can't verify docs build in CI
  24. No tox support - multi-environment testing not configurable
  25. No pyupgrade/refurb - code modernization tools

  Java:

  26. No Error Prone support - Google's bug checker not available
  27. No Sonar support - common enterprise requirement
  28. No Gradle wrapper generation - scaffold uses plain gradle
  29. No Kotlin support (with Java projects) - mixed Java/Kotlin common
  30. No JFrog/Nexus artifact publishing - only build, not deploy

  ---
  🟤 OPERATIONAL GAPS (Admin/Enterprise Features)

  31. No Config Templates for Teams

  - Profiles exist but no way to define org-wide "standard Python config"
  - Suggested: cihub template create --from-repo X --name org-python

  32. No Compliance Report Export

  - Can see tool results but no consolidated compliance report
  - Suggested: cihub report compliance --format pdf for auditors

  33. No Historical Threshold Tracking

  - Can't see if coverage has been trending down over time
  - Gate history exists in triage but not as standalone feature
  - Suggested: cihub metrics history --repo X --days 30

  34. No Notification Customization

  - Slack only, no email/Teams/Discord/PagerDuty
  - Can't customize message format
  - Suggested: Add more notification providers and templates
  - I dont do slack so for now we could do email or texting
  - This is low priority though

  35. No Multi-Repo Dashboard Out of the Box

  - cihub report dashboard generates static HTML
  - No live dashboard with drill-down
  - Suggested: Add simple web server mode or Grafana export

  ---
  TOP 10 PRIORITY RECOMMENDATIONS

  Based on user impact and architectural fit:
  ┌──────────┬────────────────────────────────────┬────────────┬─────────────┐
  │ Priority │              Feature               │ Complexity │ User Impact │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 1        │ Pre-commit hook generation         │ Low        │ Very High   │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 2        │ Branch-specific configs            │ Medium     │ High        │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 3        │ Custom tool arguments (extra_args) │ Low        │ High        │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 4        │ Matrix testing (multi-version)     │ Medium     │ High        │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 5        │ cihub ci --dry-run                 │ Low        │ Medium      │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 6        │ Profile preview in wizard          │ Low        │ Medium      │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 7        │ Config diff between repos          │ Low        │ Medium      │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 8        │ IDE config generation              │ Medium     │ Medium      │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 9        │ Scheduled scan support             │ Medium     │ Medium      │
  ├──────────┼────────────────────────────────────┼────────────┼─────────────┤
  │ 10       │ Test parallelization config        │ Low        │ Medium      │
  └──────────┴────────────────────────────────────┴────────────┴─────────────┘
  ---
  Quick Wins Already In Architecture

  These fit the existing patterns and could be added quickly:

  1. extra_args field - Just add to schema, pass through to runners
  2. cihub ci --dry-run - Strategy pattern already has tool lists
  3. Pre-commit generation - Tool registry already knows what linters exist
  4. Config diff - Just compare two loaded configs
  5. Profile preview - Metadata already in profile YAML files

  ---
  Would you like me to dive deeper into any of these gaps, or create a plan for implementing specific ones?

