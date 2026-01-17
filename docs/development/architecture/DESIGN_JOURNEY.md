# Design Journey: The Evolution of CI/CD Hub

**Status:** reference  
**Owner:** Development Team  
**Source-of-truth:** manual  
**Last-reviewed:** 2026-01-15  
**Created:** 2026-01-05  
**Author:** Justin Guida  
**Purpose:** Technical development document showing the architectural evolution of CI-HUB.  

---

## Table of Contents

| Part | Topic | Key Takeaway |
|---------------------------------------------------------------|-------------------------|-------------------------------------------|
| [Part 1](#part-1-origins---ci-cd-hub-v0-oct-23---nov-21-2025) | Origins - ci-cd-hub v0 | Over-engineering kills projects |
| [Part 2](#part-2-the-pivot-nov-21---dec-13-2025) | The Pivot | Build what you actually need |
| [Part 3](#part-3-building-hub-release-dec-14-2025---present) | Building hub-release | Thin workflows, smart CLI |
| [Part 4](#part-4-how-i-learned-to-test-for-real) | Testing (For Real) | Property-based testing changed everything |
| [Part 5](#part-5-why-i-started-writing-adrs) | Writing ADRs | Document decisions as you make them |
| [Part 6](#part-6-patterns-i-learned) | Patterns I Learned | Strategy, Facade, Registry, Table-Driven |
| [Part 7](#part-7-whats-next) | What's Next | TypeScript CLI, test reorganization |
| [Part 8](#part-8-what-i-kept-from-ci-cd-hub1) | What I Kept | Strangler Fig pattern for old code |
| [Part 9](#part-9-what-i-actually-learned) | What I Actually Learned | Ship constantly, document as you go |

---

## Quick Stats

| Metric | ci-cd-hub1 (v0) | hub-release (v1) | Growth |
|---------------------------------|---------------------------|------------------------------------|-----------|
| Timeline | Oct 23 - Nov 21 (30 days) | Dec 14 - Jan 5 (22 days) | -27% time |
| Commits | 230 | 399 | +73% |
| Python LOC | 6,890 | 27,419 | +298% |
| Tests | ~50 | 2,646 | +4,140% |
| Test Files | ~10 | 79 | +690% |
| ADRs | 0 | 44 | ∞ |
| CLI Commands | 0 | 87 (28 top-level + 59 subcommands) | ∞ |
| Files Changed (last 50 commits) | - | 335 (+48,335 / -13,619 lines) | - |

---

## Part 1: Origins - ci-cd-hub v0 (Oct 23 - Nov 21, 2025)

### 1.1 My Original Vision

My plan was to build an enterprise-grade "CI Intelligence Hub" targeting SLSA Level 3 compliance but I didn't fully understand the architecture. I decided to learn by doing, which resulted in a sprawling codebase with many half-finished features.

**Original repo structure:**
```
ci-cd-hub1/
├── tools/ # 30+ Python/Bash tools
│ ├── rekor_monitor.sh # Transparency log monitoring (500+ lines)
│ ├── cache_sentinel.py # Cache integrity with cosign signing
│ ├── dr_drill/ # Disaster recovery automation
│ ├── mutation_observatory/ # Mutation testing harness
│ └── verify_provenance.py # SLSA attestation verification
├── scripts/ # 33 automation scripts
│ ├── emit_pipeline_run.py # NDJSON telemetry emitter
│ ├── test_kyverno_policies.py
│ └── deploy_kyverno.sh
├── policies/ # Kyverno + OPA/Rego policies
├── models/ # dbt analytics marts
├── schema/ # NDJSON telemetry schemas
└── plan.md # 2,267-line master plan
```

### 1.2 Technical Stack (v0)

| Layer | Technology | Purpose |
|--------------|-------------------------------|----------------------------|
| Supply Chain | Cosign, Rekor, SLSA, SBOM/VEX | Attestation & verification |
| Policy | Kyverno, OPA/Rego | Admission control |
| Analytics | dbt-core, BigQuery | Telemetry marts |
| Chaos | DR drills, determinism checks | Resilience testing |

### 1.3 What I Learned (The Hard Way)

1. **Scope creep kills projects.** I over-engineered for hypothetical enterprise use cases instead of building a well-scoped tool that solved my real problem.
2. **Security theater ≠ security.** SLSA L3 compliance means nothing without a production workload. At the time, I didn't even know what SLSA meant for my use case.
3. **Telemetry without consumers is waste.** I built dbt marts that nobody queried.
4. **Shell scripts don't scale.** `rekor_monitor.sh` at 500+ lines was unmaintainable. I didn't understand I could have a CLI tool driving the logic instead of inline bash in YAML.
5. **Lack of documentation = lost context.** No ADRs or architecture docs meant I forgot why I made key decisions.

### 1.4 My Honest Assessment

From ci-cd-hub1's README:
> "~85% ready for trusted single-repository use... Multi-repository hub features remain in progress."

Translation: Over-engineered for a problem I didn't even have.

---

## Part 2: The Pivot (Nov 21 - Dec 13, 2025)

### What Changed and Why

As time went on, I learned more about GitHub Actions, CI/CD best practices, security frameworks, and what I actually needed as a solo developer. Through my coursework (CS305 Software Security, CS320 Software Testing) and my own projects, I started to understand what tools I needed, when to use them, and how to design proper pipelines.

### The Learning Path: Project by Project

Each project taught me something specific. Here's the actual progression:

---

#### 1. [software-testing-handbook](https://github.com/jguida941/software-testing-handbook) (CS305)

**What it was:** A deliberately vulnerable Spring Boot app for my software security class.

**What I learned:**
- How to audit dependencies for CVEs using OWASP Dependency-Check
- Vulnerability remediation: I reduced 162 CVEs down to 18
- The difference between "secure enough" and "actually secure"
- Spring Boot basics (version 3.3.5)

**Key takeaway:** Security isn't a feature you add later; it's baked into dependency choices.

---

#### 2. [checksum-and-cert-toolkit](https://github.com/jguida941/checksum-and-cert-toolkit) (CS305)

**What it was:** A small Spring Boot app that generates SHA-256 checksums and serves them over HTTPS.

**What I learned:**
- SHA-256 message digests and cryptographic hashing
- Java Keytool for generating self-signed certificates
- PKCS12 keystores and certificate management
- How to configure HTTPS/TLS in Spring Boot
- My first Architecture Decision Records (ADRs): I realized documenting "why" matters

**Key takeaway:** I finally understood what SSL/TLS actually does, not just that "it's secure."

---

#### 3. [spring-boot-ssl-demo](https://github.com/jguida941/spring-boot-ssl-demo) (CS305)

**What it was:** A demo REST API for a fictional financial company requiring secure data transmission.

**What I learned:**
- Proper HTTPS implementation on localhost
- REST API design basics
- How to write security documentation and reports
- Continued using ADRs to document decisions

**Key takeaway:** This connected the dots: I could now build secure APIs from scratch.

---

#### 4. [contact-suite-spring-react](https://github.com/jguida941/contact-suite-spring-react/tree/original-cs320): Original CS320 Version

**What it was:** My CS320 Software Testing final project. A Contact/Task/Appointment CRUD service with in-memory storage.

**What I started with:** 15 Java files, 2 CI workflows, 14 ADRs, no database, no frontend, no security.

**What I learned for the first time:**

| Tool | What I Learned |
|------------------------|--------------------------------------------------------|
| JUnit 5 | Proper unit testing, not just "it runs" |
| Validation patterns | Centralized validation helper class |
| JaCoCo | Code coverage and why 80% isn't magic |
| PITest | Mutation testing (this changed how I think about tests)|
| SpotBugs | Static analysis for bug detection |
| OWASP Dependency-Check | CVE scanning in CI |
| Checkstyle | Enforced code style |

**Key takeaway:** Mutation testing showed me when my tests were actually weak. Green checkmarks don't mean good tests.

---

#### 5. [contact-suite-spring-react](https://github.com/jguida941/contact-suite-spring-react/tree/master): Extended Version

**What happened:** After the class ended, I kept building. I wanted to see how far I could take it.

| Metric | Original | Final | Growth |
|--------------|----------|-------|--------|
| Java files | 15 | 182 | 12x |
| ADRs | 14 | 54 | 4x |
| CI workflows | 2 | 7 | 3.5x |

**New things I added:**

| Technology | What It Gave Me |
|-----------------------------------------|---------------------------------------------|
| Spring Boot 4.0 + Spring Security + JWT | Real authentication |
| Spring Data JPA + PostgreSQL + Flyway | Actual persistence with migrations |
| Testcontainers | Integration tests with real PostgreSQL in CI|
| React 19 + TypeScript + Vite | Built a real frontend |
| ZAP security scanning + API fuzzing | Found bugs I never would have caught |
| Matrix builds | Java 17/21, Ubuntu/Windows |

**Key takeaway:** A "complete" project is never complete. But more importantly, I learned *when to stop*: I had enough tools.

---

### The Moment It Clicked

After setting up the same CI pipelines (JaCoCo, PITest, SpotBugs, Dependency-Check, CodeQL) for the 100th time, I asked myself:

> *"Why am I rebuilding these workflows between repos? Why not automate this?"*

That's where CI-Hub came from. Not from reading about "enterprise CI/CD architecture", but from getting tired of repeating things that can be automated.

### 2.1 Gap Analysis

| What I Had | What I Actually Needed |
|----------------------------|------------------------|
| SLSA L3 provenance | Tests that pass |
| Kyverno admission policies | Ruff + mypy checks |
| dbt analytics marts | Coverage reports |
| Chaos engineering | A working `make test` |
| 2,267-line plan.md | A simple CLI |

### 2.2 The Decision

Start fresh with a focused goal: **"One command to run CI for any of my repos."**

The code in `_quarantine/` is salvaged from ci-cd-hub1: supply chain tools staged for future integration via the Strangler Fig pattern.

---

## Part 3: Building hub-release (Dec 14, 2025 - Present)

### How It Actually Went

I'm not going to pretend this was a clean, linear process. Here's what really happened:

**Dec 14: The First Commit:**
Started with a simple idea: a Python CLI that could run CI tools. Wrote ADR-0001 (Central vs Distributed Execution) because I'd learned from contact-suite that documenting decisions matters.

**Dec 15: 60 Commits in One Day:**
Got excited. Built workflow templates, fixture repos for testing, first aggregation logic. Looking back, some of this was over-engineered, but I was learning what I actually needed.

**Dec 26: The "Thin Workflow" Moment:**
This was the major one. I realized I was still writing bash inside YAML, the same mistake I'd made before. Moved 1000+ lines of YAML logic into the CLI. ADR-0031 documents this decision: *"Workflows should be dumb. The CLI should be smart."* 69 commits that day.

**Dec 30: CLI Became the Source of Truth:**
Added `cihub check` with tiered validation (fast/audit/security/full). Added `cihub docs`, `cihub scaffold`, ADR commands. The CLI was becoming the thing I'd wanted from the start.

**Jan 1-2: Service Layer:**
Extracted services: aggregation, discovery, triage, report_validator. This is when I started thinking about the code as layers, not just "a CLI."

**Jan 3: The Big Refactor (Phases 0-8):**
The codebase was getting messy. Single files were doing too much. Did a systematic refactor:

| Phase | What Changed |
|-------|-------------------------------------------------------------------|
| 0 | Added safety rails (import tests so I'd know if I broke something)|
| 1-2 | Extracted utilities and centralized tool definitions |
| 3-4 | Converted big files into packages |
| 5-8 | Split core modules, extracted services |

Tests went from 50 to 1,800+. Not because I was trying to hit a number, but because I was refactoring and needed to know I wasn't breaking things.

**Jan 4-5: Patterns Locked In:**
Ran a maintainability audit. Found 50 issues, 17 high-priority. Wrote ADRs for the patterns I'd discovered:

| ADR | Pattern |
|------|------------------------------------------------------|
| 0041 | Language Strategy Pattern (no more if/else chains) |
| 0042 | CommandResult Pattern (structured output for future GUI)|
| 0038 | GateSpec Registry (table-driven thresholds) |

**Tests: 2,120 passing.**

### The Modularization in Detail

Here's what each phase actually did:

| Phase | Commit | Change | Impact |
|-------|-----------|--------------------------------------------|--------------------------------------|
| 0 | `a1005f5` | Baseline + safety rails | Import tests prevent regressions |
| 1a | `44b754e` | Extract `_parse_env_bool`, `_bar` to utils | -50 lines from cli.py |
| 1b | `81162aa` | Extract CLI helpers, create types.py | CommandResult dataclass |
| 2 | `e0c4434` | Centralize tool definitions | `cihub/tools/registry.py` |
| 3a | `a3083d7` | hub_ci.py → package | 6 submodules created |
| 3b | `ca13c0b` | report.py → package | 4 submodules created |
| 4 | `65fe270` | ci_engine.py → package | gates.py, helpers.py split |
| 5 | `9cb5c30` | Core module organization | aggregation/, ci_runner/, languages/ |
| 6 | `08a5358` | CLI parser extraction | cli_parsers/ package |
| 7 | `57ac9eb` | Config loader modularization | config/loader/ package |
| 8 | `7a4bc0e` | Service extraction | 12 service modules |

### 3.3 Package Structure (Current)

```
cihub/
├── cli.py # 366 lines (was 500+), thin adapter
├── cli_parsers/ # Argument parser definitions
├── commands/ # 25 command modules
│ ├── hub_ci/ # 47 subcommands (workflow automation)
│ │ ├── router.py # Subcommand dispatch
│ │ ├── validation.py # 8 functions → CommandResult
│ │ ├── security.py # 6 functions → CommandResult
│ │ ├── python_tools.py
│ │ ├── java_tools.py
│ │ └── release.py # 16 functions → CommandResult
│ └── report/ # 11 subcommands
├── config/
│ └── loader/ # Schema validation + merge
├── core/
│ ├── aggregation/ # Multi-repo report aggregation
│ ├── ci_runner/ # Tool execution (subprocess isolation)
│ ├── gate_specs.py # 27 ThresholdSpecs (Python: 15, Java: 12)
│ └── languages/ # Strategy pattern (Python/Java)
├── services/
│ ├── ci_engine/ # gates.py, helpers.py (CI execution core)
│ ├── triage/ # Failure analysis (reference modularization)
│ ├── report_validator/ # schema/content/artifact validators
│ ├── discovery.py
│ └── aggregation.py
├── tools/
│ └── registry.py # Tool definitions (single source of truth)
├── utils/
│ ├── github_context.py # OutputContext dataclass
│ └── project.py # get_repo_name, detect_java_project_type
├── output/
│ └── renderers.py # OutputRenderer ABC, HumanRenderer, JsonRenderer
└── types.py # CommandResult, ToolResult dataclasses
```

---

## Part 4: How I Learned to Test (For Real)

### The Test Count Tells a Story

| Date | Tests | What Was Happening |
|--------|-----------|---------------------------------|
| Dec 14 | ~0 | Just started, no tests yet |
| Dec 15 | ~50 | Basic CLI tests: "does it run?" |
| Dec 26 | ~200 | Command handler tests |
| Dec 30 | ~500 | Service layer tests |
| Jan 2 | ~1,200 | Parameterized tests |
| Jan 3 | ~1,800 | Property-based testing |
| Jan 5 | **2,104** | Added contract tests |

I didn't set out to write 2,000 tests. The number grew because:
1. I was refactoring and needed confidence I wasn't breaking things
2. I discovered testing techniques that made writing tests easier
3. Property-based testing generates hundreds of test cases from one function

### Testing Techniques I Learned over Time

**Parameterized Tests:** Write once, test many cases:
```python
@pytest.mark.parametrize("tool,expected", [
 ("ruff", True), ("mypy", True), ("invalid", False)
])
def test_tool_enabled(tool, expected):
 assert tool_enabled(config, tool) == expected
```

**Property-Based Testing (Hypothesis):**
This was a game-changer. Instead of writing specific test cases, you describe *properties* that should always be true:
```python
@given(st.dictionaries(st.text(), st.booleans()))
def test_config_merge_is_associative(config):
 # Hypothesis generates hundreds of random configs
 # and checks if my merge function handles them all
 ...
```

**Mutation Testing (mutmut):**
I learned this from contact-suite and other projects. It showed me when my tests were actually weak. I had tests that passed but didn't catch bugs.

**Contract Tests:**
These prevent me from accidentally breaking the output format:
```python
def test_no_print_in_commands():
 """Commands must return CommandResult, not print()"""
 for file in glob("cihub/commands/**/*.py"):
 tree = ast.parse(file.read_text())
 assert not has_print_calls(tree), f"Print in {file}"
```

### What I Still Need to Do

Right now all 79 test files are flat in `tests/`. I need to organize them:

```
tests/
├── unit/ # Fast, isolated
├── integration/ # Cross-module
├── e2e/ # Full workflows
├── contracts/ # Schema/API contracts
└── property/ # Hypothesis tests
```

This is tracked in `TEST_REORGANIZATION.md`.

---

## Part 5: Why I Started Writing ADRs

### The Lesson from ci-cd-hub1

ci-cd-hub1 had 0 ADRs! When I came back to it later, I couldn't remember why I made certain decisions.
I'd look at code and think "why did I do it this way?" So for hub-release, I started documenting decisions
from day 1.

### Key ADRs

| # | Date | What I Decided |
|------|--------|------------------------------------------------------|
| 0001 | Dec 14 | Central execution by default (Hub runs the logic) |
| 0031 | Dec 26 | **The big one:** Workflows are dumb, CLI is smart |
| 0041 | Jan 5 | Use Strategy pattern instead of if/else chains |
| 0042 | Jan 5 | All commands return structured data (for future GUI) |

### ADR-0031: The "Thin Workflow" Decision

This changed everything. I realized I was still writing bash inside YAML:

**Before:**
```yaml
# 1000+ lines of this
- run: |
 threshold=$(echo '${{ inputs.coverage_min }}' | ...)
 if [[ "$coverage" -lt "$threshold" ]]; then
 echo "::error::Coverage below threshold"
 exit 1
 fi
```

**After:**
```yaml
# 20 lines total
- run: pip install cihub
- run: cihub ci --correlation-id "${{ inputs.hub_correlation_id }}"
```

The logic moved into Python where I could test it.

### ADR-0041: Strategy Pattern

I had 46 places in the code that looked like this:

```python
if language == "python":
 tools = ["ruff", "mypy", "pytest", "bandit"]
elif language == "java":
 tools = ["checkstyle", "pmd", "spotbugs"]
```

I learned about the Strategy pattern and refactored to:

```python
class PythonStrategy(LanguageStrategy):
 def get_default_tools(self):
 return ["ruff", "mypy", "pytest", "bandit", "pip-audit"]

# Now adding a new language is just a new class
```

### ADR-0042: CommandResult Pattern

I knew I wanted to build a GUI eventually (TypeScript CLI, maybe PyQt). So I made all commands return structured data:

```python
@dataclass
class CommandResult:
 exit_code: int
 summary: str = ""
 problems: list[dict] = field(default_factory=list)
 data: dict = field(default_factory=dict)
```

The CLI can render it as text or JSON. A future GUI can render it however it wants.

---

## Part 6: Patterns I Learned

I didn't learn these patterns from a textbook. I discovered them by having problems and then finding out the problems had names.

| Pattern | Where I Used It | What Problem It Solved |
|-------------------|---------------------------|--------------------------------------------|
| **Strangler Fig** | `_quarantine/` | Migrating old code without breaking things |
| **Strategy** | `cihub/core/languages/` | 46 if/else chains → one class per language |
| **Facade** | `cihub/config/loader/` | Config loading was scattered everywhere |
| **Registry** | `cihub/tools/registry.py` | Tool definitions were duplicated |
| **Headless API** | `CommandResult` | CLI output that a GUI can consume |
| **Schema-First** | `schema/*.json` | Validate config before running |
| **Table-Driven** | `gate_specs.py` | 27 thresholds without 27 if statements |

---

## Part 7: What's Next

### Active Design Docs

I have a few things I'm working on:

| Doc | Status | What It's For |
|--------------------------|-----------|------------------------------------|
| CLEAN_CODE.md | Archived (complete) | Output normalization complete |
| TEST_REORGANIZATION.md | Planning | Organizing 2,100+ tests |
| TYPESCRIPT_CLI_DESIGN.md | Planning | Interactive terminal UI |
| PYQT_PLAN.md | Deferred | Desktop GUI (later) |

### TypeScript CLI (The Next Big Thing)

I want to build an interactive CLI like Claude Code. Where you can type commands and see formatted output. The Python CLI would run in the background as a "headless API."

That's why I spent time on the CommandResult pattern. The Python CLI outputs JSON, and the TypeScript CLI renders it nicely.

### What I Need to Ship for v1.0

**Quick wins:**
- `cihub docs stale`: find stale code references
- `cihub docs audit`: check doc lifecycle
- `--json` flag working for all commands

**Bigger tasks:**
- Centralize all the `GITHUB_*` environment reads
- Clean up subprocess boundaries

---

## Part 8: What I Kept from ci-cd-hub1

Not everything from the first project was wasted. Some of it lives in `_quarantine/`:

| Tool | Status | Why I'm Keeping It |
|---------------------|-------------|------------------------------------------|
| `rekor_monitor.sh` | Quarantined | Supply chain verification: useful later |
| `cache_sentinel.py` | Quarantined | Cache integrity checking |
| `dr_drill/` | Quarantined | Chaos testing scripts |
| SLSA provenance | Deferred | I'll add this after v1.0 |

The "Strangler Fig" pattern means I can gradually integrate these instead of throwing them away.

---

## Part 9: What I Actually Learned

### Technical

| Lesson | Why It Matters |
|-------------------------------------|-------------------------------------------------------------------|
| Build something that works first | A working CLI beats a perfect architecture diagram |
| Tests tell you when you're breaking things | I couldn't have done the Phase 0-8 modularization without tests |
| If/else chains don't scale | 27 thresholds in a table is manageable. 27 if statements isn't |
| Write down why you made decisions | 44 ADRs means I can come back in 6 months and understand my code |

### Process

| Principle | In Practice |
|-----------------------|------------------------------------------------------------------|
| Pivot when stuck | ci-cd-hub1 wasn't the right approach, but I learned from it |
| Ship constantly | 399 commits in 22 days. Small changes, often |
| Document as you go | Not after, during |

### What I'd Do Differently

| Change | Reason |
|-------------------------------|-----------------------------------------------------------|
| Write ADRs from the start | ci-cd-hub1 has 0. I regret that |
| Start with property-based tests | They catch edge cases I never would have thought of |
| Don't over-engineer | Start small, grow as needed |

---
