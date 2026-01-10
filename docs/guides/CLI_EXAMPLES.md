# CLI Examples

> **Quick Reference** — This is a companion to [GETTING_STARTED.md](GETTING_STARTED.md).
> Use this for copy-paste commands. For full context, see the Getting Started guide.

Practical, copy-paste command examples. For full flags and options, see `docs/reference/CLI.md` or run `python -m cihub <command> --help`.

---

## Quickstart

```bash
# Scaffold a minimal repo and smoke test it
WORKDIR=$(mktemp -d)
python -m cihub scaffold python-pyproject "$WORKDIR/cihub-sample"
python -m cihub smoke "$WORKDIR/cihub-sample"

# Full smoke test (runs cihub ci)
python -m cihub smoke --full "$WORKDIR/cihub-sample"
```

---

## Repo Setup (Distributed Mode)

```bash
python -m cihub detect --repo /path/to/repo
python -m cihub init --repo /path/to/repo --apply
python -m cihub validate --repo /path/to/repo
```

Update workflow/config after changes:

```bash
python -m cihub update --repo /path/to/repo --apply
```

---

## Run CI Locally

```bash
python -m cihub ci --repo /path/to/repo --install-deps
python -m cihub run ruff --repo /path/to/repo
```

Debug and verbose modes:

```bash
CIHUB_DEBUG=True CIHUB_VERBOSE=True python -m cihub ci --repo /path/to/repo
CIHUB_EMIT_TRIAGE=True python -m cihub ci --repo /path/to/repo
```

Outputs:

```bash
ls /path/to/repo/.cihub
cat /path/to/repo/.cihub/report.json
cat /path/to/repo/.cihub/summary.md
```

---

## Fix (Auto-Fix and Analysis)

Run all auto-fixers (safe, deterministic):

```bash
cihub fix --safe                        # Auto-fix Python (ruff, black, isort) or Java (spotless)
cihub fix --safe --repo /path/to/repo   # Specific repo
cihub fix --safe --dry-run              # Preview what would be fixed
```

Run all analyzers and report issues for manual review:

```bash
cihub fix --report                      # Human-readable report
cihub fix --report --json               # JSON output for tooling
cihub fix --report --ai                 # Generate AI-consumable markdown (.cihub/fix-report.md)
```

Python tools (--report): mypy, bandit, pip_audit, semgrep, trivy
Java tools (--report): spotbugs, checkstyle, pmd, owasp, semgrep, trivy

---

## Reports

```bash
python -m cihub report build --repo /path/to/repo
python -m cihub report summary --report /path/to/repo/.cihub/report.json
python -m cihub triage --output-dir /path/to/repo/.cihub
python -m cihub report outputs --report /path/to/repo/.cihub/report.json
python -m cihub report aggregate --dispatch-dir dispatch-artifacts --output hub-report.json
python -m cihub report aggregate --reports-dir reports --output hub-report.json
```

---

## Triage (CI Failure Analysis)

Analyze local CI output:

```bash
cihub triage                                    # From local .cihub/report.json
cihub triage --output-dir ./out                 # Custom output directory
cihub triage --report path/to/report.json       # Custom report path
cihub triage --min-severity high                # Only show high+ severity failures
cihub triage --category security                # Only show security failures
cihub triage --min-severity high --category security  # Combine filters
```

Analyze remote GitHub workflow runs:

```bash
cihub triage --run 20756904005                  # Specific run ID
cihub triage --latest                           # Most recent failed run (auto-detect)
cihub triage --latest --workflow hub-ci.yml     # Filter by workflow
cihub triage --latest --branch main             # Filter by branch
cihub triage --repo owner/name --latest         # Different repository
```

Watch for failures (background daemon):

```bash
cihub triage --watch                            # Poll every 30s
cihub triage --watch --interval 60              # Poll every 60s
cihub triage --watch --workflow hub-ci.yml      # Filter by workflow
```

Multi-report mode (orchestrator runs):

```bash
cihub triage --run <ID> --aggregate             # Combine into single bundle
cihub triage --run <ID> --per-repo              # Separate bundles with index
cihub triage --multi --reports-dir ./artifacts  # Local multi-report
```

Historical analysis:

```bash
cihub triage --gate-history                     # Gate status changes over time
cihub triage --detect-flaky                     # Flaky test pattern detection
```

Outputs (in `.cihub/runs/{run_id}/` for remote, `.cihub/` for local):

```bash
cat .cihub/triage.json      # Full structured bundle
cat .cihub/priority.json    # Sorted failures only
cat .cihub/triage.md        # LLM prompt pack (AI-consumable summary)
cat .cihub/history.jsonl    # Append-only run history
```

---

## Registry (Tier-Based Config Management)

List repos and their tiers:

```bash
cihub registry list                             # All repos with effective settings
cihub registry list --tier standard             # Filter by tier
cihub registry show canary-python               # Detailed config for a repo
```

Modify tier or thresholds:

```bash
cihub registry set canary-python --tier strict  # Change tier
cihub registry set canary-python --coverage 80  # Add threshold override
cihub registry add new-repo --tier relaxed      # Add new repo to registry
```

Sync settings to repo configs:

```bash
cihub registry diff                             # Show drift from registry
cihub registry sync --dry-run                   # Preview changes
cihub registry sync --yes                       # Apply changes
```

---

## Hub-Side Configs

Create a repo config:

```bash
python -m cihub new my-repo --owner my-org --language python
```

Inspect and edit:

```bash
python -m cihub config --repo my-repo show
python -m cihub config --repo my-repo set python.tools.pytest.min_coverage 80
python -m cihub config --repo my-repo enable bandit
python -m cihub config --repo my-repo disable mutmut
python -m cihub config --repo my-repo edit
```

Emit workflow outputs for Actions:

```bash
python -m cihub config-outputs --repo /path/to/repo --github-output
```

---

## Docs & ADRs

Generate and check reference docs:

```bash
python -m cihub docs generate                    # Generate CLI.md, CONFIG.md
python -m cihub docs check                       # Verify generated docs are up-to-date
python -m cihub docs links                       # Check internal links
python -m cihub docs links --external            # Also check external URLs (requires lychee)
```

Detect stale documentation references:

```bash
python -m cihub docs stale                       # Check last 10 commits
python -m cihub docs stale --since main          # Check against main branch
python -m cihub docs stale --fail-on-stale       # CI mode - fail if stale refs found
python -m cihub docs stale --ai                  # Generate AI-consumable markdown
python -m cihub docs stale --output-dir .cihub/tool-outputs  # Write JSON + prompt pack
```

Audit documentation structure and metadata:

```bash
python -m cihub docs audit                       # Full audit (lifecycle, ADR, references)
python -m cihub docs audit --skip-references     # Fast mode - skip path scanning
python -m cihub docs audit --json                # Machine-readable output
python -m cihub docs audit --output-dir .cihub/tool-outputs  # Write docs_audit.json
```

ADR management:

```bash
python -m cihub adr list                         # List all ADRs
python -m cihub adr new "Add new workflow policy"  # Create new ADR
python -m cihub adr check                        # Validate ADR structure
```

---

## Secrets & Templates

```bash
python -m cihub setup-secrets --verify
python -m cihub setup-secrets --all
python -m cihub setup-nvd --verify
python -m cihub sync-templates --check
python -m cihub sync-templates --repo owner/name
```

---

## Java Helpers

```bash
python -m cihub fix-pom --repo /path/to/java-repo --apply
python -m cihub fix-deps --repo /path/to/java-repo --apply
```

---

## Hub CI Helpers

Use these to run hub checks locally (mirrors parts of hub-production CI):

```bash
python -m cihub hub-ci ruff --path .
python -m cihub hub-ci black --path .
python -m cihub hub-ci bandit --path .
python -m cihub hub-ci pip-audit --path .
python -m cihub hub-ci mutmut --workdir . --output-dir .cihub
python -m cihub hub-ci validate-configs
python -m cihub hub-ci validate-profiles
python -m cihub hub-ci validate-triage                        # Validate triage.json against schema
python -m cihub hub-ci license-check
```

Full list:

```bash
python -m cihub hub-ci --help
```

---

## Local Validation Wrapper

```bash
python -m cihub check
python -m cihub verify
python -m cihub verify --remote
python -m cihub verify --remote --integration --install-deps
make verify
```

Advanced options:

```bash
python -m cihub check --smoke-repo /path/to/repo --install-deps
python -m cihub check --relax --keep
```
