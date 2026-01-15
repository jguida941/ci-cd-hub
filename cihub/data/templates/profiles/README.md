# CI/CD Hub Profiles

Pre-configured tool combinations for common CI/CD scenarios.

## Available Profiles

| Profile | Language | Description | Expected Runtime |
|---------|----------|-------------|------------------|
| `java-minimal.yaml` | Java | Fastest sanity check (tests only) | ~3-6 min |
| `java-fast.yaml` | Java | Quick feedback for PRs | ~5-10 min |
| `java-quality.yaml` | Java | Thorough analysis for releases | ~15-30 min |
| `java-coverage-gate.yaml` | Java | High coverage/mutation bars | ~15-25 min |
| `java-compliance.yaml` | Java | Security/compliance focus | ~20-40 min |
| `java-security.yaml` | Java | Full security scanning | ~20-40 min |
| `python-minimal.yaml` | Python | Fastest sanity check (lint+tests) | ~2-5 min |
| `python-fast.yaml` | Python | Quick feedback for PRs | ~3-8 min |
| `python-quality.yaml` | Python | Thorough analysis for releases | ~15-30 min |
| `python-coverage-gate.yaml` | Python | High coverage/mutation bars | ~12-20 min |
| `python-compliance.yaml` | Python | Security/compliance focus | ~15-30 min |
| `python-security.yaml` | Python | Full security scanning | ~15-30 min |

_Expected runtimes are rough estimates and depend on repo size and runner speed._

## Precedence and merge rules
- Profile values are merged into hub config (`config/repos/*.yaml`), then overridden by a repo’s `.ci-hub.yml` (repo wins).
- Use one source of truth for thresholds: prefer `thresholds.*`; tool-level `min_*` defaults are just starting points.
- Only the language block matching `repo.language` is used; ignore/remove the other language block.
- For quick gates without full profiles, use `thresholds_profile` (`coverage-gate`, `security`, `compliance`) and override via `thresholds.*`.

## When to Use Each Profile

### Minimal Profile
- **Use for:** Docs-only PRs, tiny repos, fast sanity checks
- **Enables:** Bare-minimum tests/lint
- **Disables:** Coverage gates, mutation, SAST, dependency/container scanning

### Fast Profile
- **Use for:** PR checks, development iteration, quick feedback
- **Enables:** Lint, tests, coverage, and formatting (black/isort on Python)
- **Disables:** Mutation testing, SAST, container scanning

### Quality Profile
- **Use for:** Pre-merge checks, release candidates, nightly builds
- **Enables:** All quality tools including mutation testing
- **Disables:** Heavy security scanning (use security profile)

### Coverage Gate Profile
- **Use for:** Release branches that must meet bars
- **Enables:** High coverage/mutation thresholds, lint (e.g., coverage 90%, mutation 80%)
- **Disables:** Security tools (pair with security/compliance profiles)

### Compliance Profile
- **Use for:** Compliance gates where scan coverage/reporting matter most
- **Enables:** Dependency + SAST + container scanning with stricter thresholds
- **Disables:** Most quality-focused tools (coverage, mutation)

### Security Profile
- **Use for:** Security-only runs (pair with Fast/Quality on another branch)
- **Enables:** All security scanners (SAST, SCA, container)
- **Disables:** Coverage/formatting; intended to complement Fast/Quality

## How to Apply a Profile

### Option 0: Use the apply_profile helper

```bash
python -m cihub config apply-profile --profile templates/profiles/python-fast.yaml --target config/repos/my-repo.yaml
python -m cihub hub-ci validate-configs
# Or validate a single repo
python -m cihub hub-ci validate-configs --repo my-repo
```

### Option 1: Copy Profile to Repo Config

```bash
# Copy profile as your repo config
cp templates/profiles/python-fast.yaml config/repos/my-repo.yaml

# Edit the repo: section at the top with your owner/name/language (and subdir if needed)
$EDITOR config/repos/my-repo.yaml
```

### Option 2: Merge Profile with Existing Config

Copy the `tools:` section from a profile into your existing config.

### Option 3: Use Multiple Profiles per Branch

Configure different workflows for different branches:
- `main`: security profile (thorough checks)
- `develop`: quality profile (pre-merge)
- PRs: fast profile (quick feedback)

## Customizing Profiles

Feel free to modify these profiles for your needs:

```yaml
# Start with fast profile, add one expensive tool
python:
 tools:
 # ... fast profile defaults ...

 # Add mypy for type checking
 mypy:
 enabled: true
```

## Profile Tool Matrix

### Java Profiles

| Tool | Minimal | Fast | Quality | Coverage Gate | Compliance | Security |
|------|---------|------|---------|---------------|------------|----------|
| JaCoCo | N | Y | Y | Y (90%) | N | N |
| Checkstyle | N | Y | Y | Y | N | N |
| SpotBugs | N | Y | Y | Y | Y | Y |
| PMD | N | N | Y | Y | N | N |
| PITest | N | N | Y | Y (80%) | N | N |
| OWASP | N | N | Y | N | Y | Y |
| Semgrep | N | N | N | N | Y | Y |
| Trivy | N | N | N | N | Y | Y |
| CodeQL | N | N | N | N | Y | Y |

### Python Profiles

| Tool | Minimal | Fast | Quality | Coverage Gate | Compliance | Security |
|------|---------|------|---------|---------------|------------|----------|
| pytest | Y | Y | Y | Y (90%) | N | N |
| ruff | Y | Y | Y | Y | N | N |
| black | N | Y | Y | Y | N | N |
| isort | N | Y | Y | Y | N | N |
| bandit | N | Y | Y | N | Y | Y |
| pip-audit | N | Y | Y | N | Y | Y |
| mypy | N | N | Y | N | N | N |
| mutmut | N | N | Y | Y (80%) | N | N |
| Semgrep | N | N | N | N | Y | Y |
| Trivy | N | N | N | N | Y | Y |
| CodeQL | N | N | N | N | Y | Y |

Notes:
- CodeQL is heavy and may require org permissions; enable intentionally.
- Use the `pip_audit` key (underscore) consistently in configs; tool names in text may show hyphens.
- Consider omitting hardcoded PITest threads; defaults adapt better to runner cores.
- Thresholds: use `thresholds.coverage_min` and `thresholds.mutation_score_min` as the source of truth; tool-level `min_*` values are defaults only.
