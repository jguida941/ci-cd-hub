# Onboarding a New Repository

This guide shows how to connect your repository to the CI/CD Hub.

**Choose your mode:**
- **Central Mode (Recommended):** Hub clones and tests repos. Repos stay clean - no workflow files needed.
- **Distributed Mode:** Repos have their own workflow files that call hub's reusable workflows.

---

## Quick Start: Central Mode (5 minutes)

The hub clones your repo and runs all CI tools. You only add a config file to the hub.

### Step 1: Create Hub Config

```bash
# Copy a profile template
cp templates/profiles/java-fast.yaml config/repos/my-repo.yaml

# Or for Python
cp templates/profiles/python-fast.yaml config/repos/my-repo.yaml
```

### Step 2: Edit Repo Metadata

Edit `config/repos/my-repo.yaml` to add your repo details:

```yaml
repo:
  owner: your-github-handle
  name: your-repo-name
  language: java  # or python
  default_branch: main

# Profile settings are already included from the template
# Only change what you need to customize
```

### Step 3: Validate and Run

```bash
# Validate your config
python scripts/validate_config.py config/repos/my-repo.yaml

# Run the hub (via GitHub Actions UI or CLI)
gh workflow run hub-run-all.yml
```

**Done!** The hub will clone your repo and run all configured tools.

---

## Advanced: Distributed Mode

Use this if your repo needs its own runners, secrets, or you prefer repo-controlled CI.

### Option A: Use cihub CLI (Recommended - 5 minutes)

Generate the caller workflow and repo-local config:
```bash
cd /path/to/your-repo
python -m cihub init --repo .
git add .ci-hub.yml .github/workflows/hub-ci.yml
git commit -m "Add hub CI caller"
git push
```

Configure hub to dispatch to this repo (if you are not relying on repo-local config):
```yaml
# config/repos/my-repo.yaml
repo:
  owner: your-github-handle
  name: your-repo-name
  language: java
  dispatch_enabled: true
  dispatch_workflow: hub-ci.yml
```

**Benefits:** The generated caller accepts all hub inputs, stays in sync with the hub templates, and produces consistent artifacts for aggregation.

### Option B: Call Reusable Workflows (15 minutes)

Alternatively, create your own workflow that calls the hub's reusable workflows.

#### Step 1: Add Hub Config (Optional)

Same as central mode - create `config/repos/my-repo.yaml` if you want the hub to track this repo.

#### Step 2: Add Workflow to Your Repo

Create `.github/workflows/ci.yml` in your repository:

#### Java Projects

```yaml
name: CI

on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/java-ci.yml@main
    with:
      java_version: '21'
      run_jacoco: true
      run_checkstyle: true
      run_spotbugs: true
      run_owasp: true
      run_pitest: false      # Expensive - enable when needed
      run_codeql: false      # Expensive - enable when needed
      coverage_min: 70
    secrets: inherit
```

#### Python Projects

```yaml
name: CI

on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@main
    with:
      python_version: '3.12'
      run_pytest: true
      run_ruff: true
      run_bandit: true
      run_pip_audit: true
      run_mutmut: false      # Expensive - enable when needed
      run_codeql: false      # Expensive - enable when needed
      coverage_min: 70
    secrets: inherit
```

### Step 3: (Optional) Add Local Overrides

Add `.ci-hub.yml` to your repo root for repo-controlled settings:

```yaml
version: "1.0"
language: java

java:
  tools:
    pitest:
      enabled: false
    jacoco:
      min_coverage: 80
    docker:
      enabled: true
```

---

## Java: Required Maven Plugins

For Java projects, ensure your `pom.xml` has the necessary plugins:

```xml
<build>
  <plugins>
    <!-- JaCoCo for coverage -->
    <plugin>
      <groupId>org.jacoco</groupId>
      <artifactId>jacoco-maven-plugin</artifactId>
      <version>0.8.11</version>
    </plugin>

    <!-- Checkstyle -->
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-checkstyle-plugin</artifactId>
      <version>3.3.1</version>
    </plugin>

    <!-- SpotBugs -->
    <plugin>
      <groupId>com.github.spotbugs</groupId>
      <artifactId>spotbugs-maven-plugin</artifactId>
      <version>4.8.3.1</version>
    </plugin>

    <!-- OWASP Dependency Check (optional) -->
    <plugin>
      <groupId>org.owasp</groupId>
      <artifactId>dependency-check-maven</artifactId>
      <version>9.0.9</version>
    </plugin>

    <!-- PITest Mutation Testing (optional) -->
    <plugin>
      <groupId>org.pitest</groupId>
      <artifactId>pitest-maven</artifactId>
      <version>1.15.3</version>
    </plugin>
  </plugins>
</build>
```

---

## Verify Setup

1. Push changes (if distributed) or trigger hub workflow (if central)
2. Check the Actions tab for the workflow run
3. Verify artifacts are generated
4. Check the summary for metrics

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Workflow file not found" | Ensure hub repo is public or you have access |
| "PITest fails" | Ensure test classes exist; disable pitest first |
| "OWASP is slow" | Add `NVD_API_KEY` secret ([get free key](https://nvd.nist.gov/developers/request-an-api-key)) |
| "Docker build fails" | Docker inputs removed from CI templates (25 input limit). Use separate `hub-*-docker.yml` template or hardcode in `with:` block |
| "Coverage is 0%" | Check test files are running; verify pytest/JaCoCo setup |

For more issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## See Also

- [CONFIG_REFERENCE.md](../reference/CONFIG_REFERENCE.md) - All config options
- [TOOLS.md](../reference/TOOLS.md) - What tools are available
- [MODES.md](MODES.md) - Central vs Distributed explained
- [DISPATCH_SETUP.md](DISPATCH_SETUP.md) - Full dispatch/orchestrator setup guide
- [TEMPLATES.md](TEMPLATES.md) - All available templates
- [templates/profiles/](../../templates/profiles/) - Pre-built profiles
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Fix common issues

## Precedence and gating
- Runtime merge (dispatch): config/defaults.yaml -> config/repos/<repo>.yaml -> repo-local .ci-hub.yml (repo wins).
- Dispatch mode merges repo-local `.ci-hub.yml` (highest precedence) over hub config when present.
- Central mode currently uses hub config only; repo-local merge is planned.
- Profiles are generation helpers only; they are merged into hub config, then repo overrides win.
- Tool steps are gated by config run_* flags (central mode) and will be once dispatch workflows are updated.
