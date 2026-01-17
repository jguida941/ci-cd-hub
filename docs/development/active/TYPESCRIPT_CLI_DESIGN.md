# TypeScript CLI Design: CIHub Interactive Terminal

**Status:** active
**Owner:** Development Team
**Source-of-truth:** manual
**Last-reviewed:** 2026-01-15

**Date:** 2026-01-05
**Status:** Planning
**Priority:** **#5** (See [MASTER_PLAN.md](../MASTER_PLAN.md#active-design-docs---priority-order))
**Depends On:** CLEAN_CODE.md (archived, complete - explicit prerequisite)
**Blocks:** PYQT_PLAN.md
**Purpose:** Design document for a Claude Code / Codex-style interactive CLI built with TypeScript and Ink (React for terminals).

---

## WARNING: PREREQUISITE

> **DO NOT START THIS UNTIL `CLEAN_CODE.md` IS COMPLETE.**
>
> The Python CLI must have clean JSON output (no print statements corrupting stdout) before the TypeScript CLI can reliably parse CommandResult JSON. Complete all tasks in `docs/development/archive/CLEAN_CODE.md` first.

---

## Master Checklist

This checklist tracks ALL implementation tasks. Check items off as they're completed.

### Phase 0: Prerequisites (CLEAN_CODE.md)
- [ ] Fix all remaining print statements in Python CLI
- [ ] Ensure all commands return clean JSON on stdout when `--json` flag is used
- [ ] Add JSON purity contract test
- [ ] Verify CommandResult schema is consistent across all commands

### Phase 1: Python CLI AI Integration (Modular)
- [ ] Create `cihub/ai/` module directory
- [ ] Create `cihub/ai/__init__.py` with public API
- [ ] Create `cihub/ai/claude_client.py` - Claude CLI subprocess wrapper
- [ ] Create `cihub/ai/context.py` - Context builder for AI
- [ ] Create `cihub/ai/enhance.py` - Result enhancement logic
- [ ] Add `--ai` flag to argument parser
- [ ] Add `--ai` support to `triage` command
- [ ] Add `--ai` support to `check` command
- [ ] Add `--ai` support to `report` commands
- [ ] Add `CIHUB_DEV_MODE` environment variable support
- [ ] Add `CIHUB_AI_PROVIDER` environment variable (default: claude)
- [ ] Write unit tests for AI module (`tests/test_ai_module.py`)
- [ ] Write integration tests for AI enhancement

### Phase 2: TypeScript CLI Foundation
- [ ] Initialize TypeScript project (`cihub-cli/`)
- [ ] Configure `tsconfig.json` with `strict: true`
- [ ] Configure `tsup.config.ts` bundler
- [ ] Set up `package.json` with dependencies
- [ ] Set up Vitest for testing
- [ ] Create entry point (`src/index.tsx`)
- [ ] Create CLI argument parser (`src/cli.ts`)
- [ ] Add version check between TypeScript and Python CLI
- [ ] Add health check for Python CLI availability

### Phase 3: Core Components
- [ ] Create `src/app.tsx` - Main App component
- [ ] Create `src/components/Header.tsx`
- [ ] Create `src/components/Input.tsx` - Command input with history
- [ ] Create `src/components/Output.tsx` - Result display
- [ ] Create `src/components/Problems.tsx` - Problem list with icons
- [ ] Create `src/components/Suggestions.tsx`
- [ ] Create `src/components/Table.tsx`
- [ ] Create `src/components/Spinner.tsx`
- [ ] Create `src/components/ErrorBoundary.tsx`

### Phase 4: Python CLI Bridge
- [ ] Create `src/lib/cihub.ts` - Subprocess wrapper
- [ ] Create `src/lib/parser.ts` - Slash command parser
- [ ] Create `src/lib/timeouts.ts` - Command-specific timeouts
- [ ] Create `src/lib/errors.ts` - Error handling utilities
- [ ] Create `src/types/command-result.ts` - Zod schemas
- [ ] Create `src/types/exit-codes.ts`
- [ ] Write contract tests (`test/contracts/`)

### Phase 5: Slash Commands
- [ ] Create `src/commands/index.ts` - Command registry
- [ ] Implement all top-level commands (27)
- [ ] Implement report subcommands (11)
- [ ] Implement config subcommands (7)
- [ ] Implement docs subcommands (5)
- [ ] Implement adr subcommands (4)
- [ ] Implement hub-ci subcommands (46)
- [ ] Implement meta commands (`/help`, `/clear`, `/exit`, etc.)

### Phase 6: Interactive Wizard
- [ ] Create `src/components/Wizard.tsx`
- [ ] Create `src/lib/wizard-steps.ts` - Step definitions with conditionals
- [ ] Create `src/lib/profiles.ts` - Profile definitions
- [ ] Implement `/new` wizard flow
- [ ] Implement `/init` wizard flow
- [ ] Implement `/config edit` wizard flow

### Phase 7: Configuration
- [ ] Create `src/lib/config.ts` - Config loader
- [ ] Create `src/context/ConfigContext.tsx`
- [ ] Define `~/.cihubrc` schema
- [ ] Implement environment variable overrides
- [ ] Create `src/components/FirstRunSetup.tsx`

### Phase 8: AI Enhancement (TypeScript Inherits from Python)
- [ ] Verify `--ai` flag passes through to Python CLI correctly
- [ ] Create `src/components/AIResponse.tsx` - AI response display
- [ ] Handle AI timeout gracefully in UI
- [ ] Show loading state during AI processing

### Phase 9: Testing
- [ ] Write unit tests for parser (`test/unit/parser.test.ts`)
- [ ] Write unit tests for config loader (`test/unit/config.test.ts`)
- [ ] Write component tests (`test/components/`)
- [ ] Write integration tests (`test/integration/`)
- [ ] Write E2E tests (`test/e2e/`)
- [ ] Achieve 80% code coverage
- [ ] Set up CI workflow for TypeScript CLI

### Phase 10: Accessibility (Critical)
- [ ] Honor `NO_COLOR` environment variable
- [ ] Honor `TERM=dumb` - disable formatting entirely
- [ ] Add `--no-animation` flag for motion sensitivity
- [ ] Add `--plain` flag for plain text output (no colors, no unicode)
- [ ] Support `CI=true` detection for non-interactive mode
- [ ] Test TTY vs non-TTY (piped) output modes
- [ ] Avoid reliance on color alone - use whitespace/indentation
- [ ] Make unicode icons optional (fallback to ASCII)
- [ ] Test output with screen reader simulation

### Phase 11: Process Management
- [ ] Handle SIGINT (Ctrl+C) gracefully
- [ ] Handle SIGTERM gracefully
- [ ] Clean up child processes on exit
- [ ] Implement graceful shutdown with timeout
- [ ] Propagate signals to Python subprocess

### Phase 12: Polish & Distribution
- [ ] Create welcome/startup screen
- [ ] Add keyboard shortcuts
- [ ] Add command history (up/down arrows)
- [ ] Add tab completion
- [ ] Bundle into single file
- [ ] Create `bin/cihub.js` entry point
- [ ] Publish to npm
- [ ] Write installation documentation

### Phase 13: Documentation
- [ ] Update README with TypeScript CLI usage
- [ ] Create slash command reference
- [ ] Document configuration options
- [ ] Create troubleshooting guide

---

## Executive Summary

Build an interactive TypeScript CLI that wraps the existing CIHub Python CLI with:

1. **React + Ink** - Same technology as Claude Code
2. **Slash commands** - `/discover`, `/triage`, `/ai`
3. **AI integration** - Natural language that translates to CLI commands
4. **npm distribution** - `npm i -g @yourorg/cihub` or `npx cihub`

**This is NOT a desktop GUI.** It runs directly in your terminal (iTerm, Terminal.app, etc.) just like Claude Code and Codex.

---

## Table of Contents

- [Part 1: What Claude Code & Codex Actually Use](#part-1-what-claude-code--codex-actually-use)
- [Part 2: Architecture](#part-2-architecture)
- [Part 3: Technology Stack](#part-3-technology-stack)
- [Part 4: Project Structure](#part-4-project-structure)
- [Part 5: Complete Slash Command Reference](#part-5-complete-slash-command-reference)
- [Part 6: AI Enhancement by Category](#part-6-ai-enhancement-by-category)
- [Part 7: Hub-CI Subcommands (46 Tools)](#part-7-hub-ci-subcommands-46-tools)
- [Part 8: Interactive Wizard System](#part-8-interactive-wizard-system)
- [Part 9: Modular AI Architecture (Python)](#part-9-modular-ai-architecture-python)
- [Part 10: Blockers & Prerequisites](#part-10-blockers--prerequisites)
- [Part 11: Implementation Phases](#part-11-implementation-phases)
- [Part 12: Code Examples](#part-12-code-examples)
- [Part 13: Distribution](#part-13-distribution)
- [Part 14: CommandResult Schema](#part-14-commandresult-schema)
- [Part 15: Testing Strategy](#part-15-testing-strategy)
- [Part 16: Error Handling Patterns](#part-16-error-handling-patterns)
- [Part 17: Configuration File Format](#part-17-configuration-file-format)
- [Part 18: Accessibility](#part-18-accessibility)
- [Part 19: Process Management](#part-19-process-management)

---

## Part 1: What Claude Code & Codex Actually Use

### Claude Code: TypeScript + React + Ink

**Source:** [How Claude Code is Built](https://newsletter.pragmaticengineer.com/p/how-claude-code-is-built)

| Component | Technology |
|---------------|---------------------------------------|
| Language | TypeScript |
| UI Framework | **React + Ink** (renders to terminal) |
| Layout Engine | Yoga (flexbox for terminal) |
| Runtime | Bun / Node.js |
| Distribution | npm (`@anthropic-ai/claude-code`) |
| Bundle Size | 10.5MB single file |

**Key insight:** Claude Code is listed on the [official Ink repository](https://github.com/vadimdemedes/ink) as "an agentic coding tool made by Anthropic."

Anthropic wrote a **custom renderer** on top of Ink for fine-grained incremental updates in long-running sessions.

### Codex CLI: Rust TUI

**Source:** [Codex GitHub](https://github.com/openai/codex)

| Component | Technology |
|--------------|----------------------------------------|
| Language | Rust (97.6%) |
| Architecture | Submission Queue / Event Queue pattern |
| Distribution | npm or Homebrew |

Originally Node.js, rewritten in Rust for zero-dependency install and native sandbox security.

### What They Have in Common

Both run **directly in your terminal** - no separate window, no Electron, no Tauri. They're npm-installable CLIs that take over your terminal with an interactive UI.

---

## Part 2: Architecture

### High-Level Flow

```
┌────────────────────────────────────────────────────────────────────┐
│ YOUR TERMINAL │
│ (iTerm, Terminal.app, Windows Terminal, etc.) │
├────────────────────────────────────────────────────────────────────┤
│ │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ CIHUB INTERACTIVE CLI │
│ │ (TypeScript + Ink) │ │
│ ├───────────────────────────────────────────────────────────────┤ │
│ │ │ │
│ │ ╭─────────────────────────────────────────────────────────╮ │ │
│ │ │ CIHub v1.0.0 ~/myproject │ │ │
│ │ ╰─────────────────────────────────────────────────────────╯ │ │
│ │ │ │
│ │ Found Python project with 3 issues: │ │
│ │ │ │
│ │ Coverage below threshold (65% < 70%) │ │
│ │ 2 security vulnerabilities detected │ │
│ │ [ ] Ruff check failed with 5 errors │ │
│ │ │ │
│ │ Suggestions: │ │
│ │ • Run `/check --fix` to auto-fix linting issues │ │
│ │ • Run `/triage` for AI-assisted remediation │ │
│ │ │ │
│ │ ╭─────────────────────────────────────────────────────────╮ │ │
│ │ │ > /triage --since HEAD~5 │ │ │
│ │ ╰─────────────────────────────────────────────────────────╯ │ │
│ │ │ │
│ └───────────────────────────────────────────────────────────────┘ │
│ │
└────────────────────────────────────────────────────────────────────┘
 │
 │ subprocess (spawn)
 ▼
┌────────────────────────────────────────────────────────────────────┐
│ PYTHON CLI (cihub) │
│ │
│ $ python -m cihub triage --since HEAD~5 --json │
│ │
│ Returns: CommandResult JSON │
│ │
└────────────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ TypeScript CLI Package │
├─────────────────────────────────────────────────────────────────┤
│ │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│ │ App.tsx │ │ Commands/ │ │ AI Bridge │ │
│ │ (Main UI) │ │ (Handlers) │ │ (Claude/Codex API) │ │
│ └──────┬───────┘ └──────┬───────┘ └──────────┬───────────┘ │
│ │ │ │ │
│ └────────┬────────┴─────────────────────┘ │
│ │ │
│ ┌────────▼────────┐ │
│ │ CLI Bridge │ │
│ │ (spawn cihub) │ │
│ └────────┬────────┘ │
│ │ │
└──────────────────┼──────────────────────────────────────────────┘
 │ subprocess
 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Python CLI (existing cihub package) │
│ │
│ cihub discover --json │
│ cihub triage --json │
│ cihub check --json │
│ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Technology Stack

### Core Technologies

| Layer | Technology | Purpose |
|-----------------|----------------------------|----------------------|
| Language | **TypeScript 5.x** | Type safety |
| UI Framework | **React 19.x + Ink 5.x** | Terminal UI |
| Layout | **Yoga** (built into Ink) | Flexbox for terminal |
| Runtime | **Node.js 20+** or **Bun** | JavaScript runtime |
| Build | **tsup** or **esbuild** | Fast bundling |
| Package Manager | **pnpm** | Fast, disk-efficient |

### Ink Ecosystem

| Package | Purpose |
|------------------------|----------------------------------|
| `ink` | Core React renderer for terminal |
| `ink-text-input` | Text input component |
| `ink-select-input` | Selection menus |
| `ink-spinner` | Loading spinners |
| `ink-table` | Table rendering |
| `ink-syntax-highlight` | Code highlighting |
| `@inkjs/ui` | Pre-built UI components |

### Additional Libraries

| Package | Purpose |
|------------------------|---------------------------------------|
| `commander` or `yargs` | CLI argument parsing |
| `execa` | Subprocess execution (run Python CLI) |
| `zod` | JSON schema validation |
| `chalk` | Color output |
| `figures` | Unicode symbols ([x], [ ], ) |

---

## Part 4: Project Structure

```
cihub-cli/
├── package.json
├── tsconfig.json
├── tsup.config.ts # Bundler config
├── bin/
│ └── cihub.js # Entry point (shebang)
├── src/
│ ├── index.tsx # Main entry
│ ├── cli.ts # Argument parsing
│ ├── app.tsx # Root Ink component
│ ├── components/
│ │ ├── Header.tsx # App header with cwd
│ │ ├── Output.tsx # Command output display
│ │ ├── Input.tsx # Command input with history
│ │ ├── Problems.tsx # Problem list with icons
│ │ ├── Suggestions.tsx # Suggestion list
│ │ ├── Table.tsx # Data tables
│ │ └── Spinner.tsx # Loading indicator
│ ├── commands/
│ │ ├── discover.ts # /discover handler
│ │ ├── triage.ts # /triage handler
│ │ ├── check.ts # /check handler
│ │ ├── ai.ts # /ai handler
│ │ └── index.ts # Command registry
│ ├── lib/
│ │ ├── cihub.ts # Python CLI bridge
│ │ ├── parser.ts # Slash command parser
│ │ └── ai-client.ts # AI API client
│ └── types/
│ ├── command-result.ts
│ └── slash-command.ts
├── test/
│ └── commands.test.ts
└── README.md
```

### package.json

```json
{
 "name": "@yourorg/cihub-cli",
 "version": "1.0.0",
 "description": "Interactive CLI for CIHub",
 "type": "module",
 "bin": {
 "cihub-interactive": "./bin/cihub.js"
 },
 "scripts": {
 "build": "tsup src/index.tsx --format esm --dts",
 "dev": "tsup src/index.tsx --watch",
 "start": "node bin/cihub.js"
 },
 "dependencies": {
 "ink": "^5.0.0",
 "ink-text-input": "^6.0.0",
 "ink-spinner": "^5.0.0",
 "react": "^19.0.0",
 "execa": "^9.0.0",
 "commander": "^12.0.0",
 "chalk": "^5.3.0",
 "figures": "^6.0.0",
 "zod": "^3.23.0"
 },
 "devDependencies": {
 "@types/react": "^19.0.0",
 "typescript": "^5.5.0",
 "tsup": "^8.0.0",
 "vitest": "^2.0.0"
 }
}
```

---

## Part 5: Complete Slash Command Reference

This section maps **ALL 92+ cihub commands** to slash commands. The goal: users never need to leave the interactive CLI.

### 5.1 Top-Level Commands (27 Commands)

| Slash Command | Python CLI | Flags | AI Enhancement |
|---------------|------------|-------|----------------|
| `/detect` | `cihub detect` | `--json` | Auto-suggest missing configs |
| `/preflight` | `cihub preflight` | `--json` | Explain failed prerequisites |
| `/scaffold` | `cihub scaffold` | `--language`, `--output-dir`, `--json` | Suggest templates |
| `/smoke` | `cihub smoke` | `--json` | Diagnose failures |
| `/smoke validate` | `cihub smoke validate` | `--json` | Explain validation errors |
| `/check` | `cihub check` | `--fix`, `--verbose`, `--json` | Auto-fix suggestions |
| `/verify` | `cihub verify` | `--json` | Interpret verification results |
| `/ci` | `cihub ci` | `--since`, `--json` | Explain CI status |
| `/run` | `cihub run` | `--language`, `--output-dir`, `--json` | Recommend optimal flags |
| `/report` | `cihub report` | (see subcommands) | Full report intelligence |
| `/triage` | `cihub triage` | `--since`, `--ai`, `--run`, `--artifacts-dir`, `--repo`, `--json` | **HIGHEST AI VALUE** |
| `/docs` | `cihub docs` | (see subcommands) | Stale doc detection |
| `/adr` | `cihub adr` | (see subcommands) | ADR suggestions |
| `/init` | `cihub init` | `--force`, `--json` | Config recommendations |
| `/update` | `cihub update` | `--json` | Update impact analysis |
| `/validate` | `cihub validate` | `--json` | Config error explanations |
| `/fix-pom` | `cihub fix-pom` | `--apply`, `--json` | Java POM recommendations |
| `/fix-deps` | `cihub fix-deps` | `--apply`, `--json` | Dependency suggestions |
| `/setup-secrets` | `cihub setup-secrets` | `--json` | Secret configuration help |
| `/setup-nvd` | `cihub setup-nvd` | `--json` | NVD API setup guidance |
| `/sync-templates` | `cihub sync-templates` | `--json` | Template update analysis |
| `/new` | `cihub new` | `--json` | Project scaffolding wizard |
| `/config` | `cihub config` | (see subcommands) | Config optimization |
| `/config outputs` | `cihub config-outputs` | `--json` | Output path suggestions |
| `/hub-ci` | `cihub hub-ci` | (46 subcommands) | Full hub-ci intelligence |
| `/discover` | `cihub discover` | `--json` | Repo analysis |
| `/dispatch` | `cihub dispatch` | `--json` | Workflow dispatch assistance |

### 5.2 Report Subcommands (11 Commands)

| Slash Command | Python CLI | Purpose | AI Value |
|---------------|------------|---------|----------|
| `/report build` | `cihub report build` | Build report.json from outputs | Consolidate findings |
| `/report summary` | `cihub report summary` | Render summary from report | Explain trends |
| `/report outputs` | `cihub report outputs` | Write workflow outputs | Automation |
| `/report aggregate` | `cihub report aggregate` | Aggregate hub reports | Cross-repo insights |
| `/report validate` | `cihub report validate` | Validate report.json | Structure fixes |
| `/report dashboard` | `cihub report dashboard` | Generate dashboard | Visual insights |
| `/report security-summary` | `cihub report security-summary` | Security summaries | Prioritize vulnerabilities |
| `/report smoke-summary` | `cihub report smoke-summary` | Smoke test summaries | Test health |
| `/report kyverno-summary` | `cihub report kyverno-summary` | Kyverno summaries | Policy insights |
| `/report orchestrator-summary` | `cihub report orchestrator-summary` | Orchestrator summaries | Workflow health |
| `/report pytest-summary` | `cihub report pytest-summary` (via hub-ci) | Pytest summaries | Test insights |

### 5.3 Docs Subcommands (5+ Commands)

| Slash Command | Python CLI | Purpose | AI Value |
|---------------|------------|---------|----------|
| `/docs check` | `cihub docs check` | Validate documentation | Error explanations |
| `/docs links` | `cihub docs links` | Check broken links | Fix suggestions |
| `/docs stale` | `cihub docs stale` (planned) | Detect stale docs | **AI-driven updates** |
| `/docs generate` | `cihub docs generate` (planned) | Generate docs | Auto-documentation |
| `/docs sync` | `cihub docs sync` (planned) | Sync with code | Keep docs current |

### 5.4 ADR Subcommands (4 Commands)

| Slash Command | Python CLI | Purpose | AI Value |
|---------------|------------|---------|----------|
| `/adr list` | `cihub adr list` | List ADRs | Summarize decisions |
| `/adr new` | `cihub adr new` | Create new ADR | Draft ADR content |
| `/adr check` | `cihub adr check` | Validate ADRs | Format suggestions |
| `/adr status` | `cihub adr status` | ADR status overview | Identify superseded ADRs |

### 5.5 Config Subcommands (7 Commands)

| Slash Command | Python CLI | Purpose | AI Value |
|---------------|------------|---------|----------|
| `/config show` | `cihub config show` | Display config | Explain settings |
| `/config edit` | `cihub config edit` | Edit config via wizard | AI-guided editing |
| `/config set` | `cihub config set` | Set a config value | Value recommendations |
| `/config enable` | `cihub config enable` | Enable a tool | Tool recommendations |
| `/config disable` | `cihub config disable` | Disable a tool | Impact analysis |
| `/config apply-profile` | `cihub config apply-profile` | Apply a profile | Profile selection help |
| `/config outputs` | `cihub config-outputs` | Show output paths | Path optimization |

### 5.6 Meta Commands (Interactive CLI Only)

| Command | Description | Shortcut |
|---------|-------------|----------|
| `/help` | Show all available commands | `?` |
| `/help <command>` | Show help for specific command | |
| `/clear` | Clear screen | Ctrl+L |
| `/exit` | Exit interactive mode | Ctrl+C |
| `/cd <path>` | Change working directory | |
| `/pwd` | Show current directory | |
| `/history` | Show command history | ↑/↓ arrows |
| `/reload` | Reload configuration | |
| `/status` | Show system status | |

### 5.7 AI-Specific Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/ai <prompt>` | Free-form AI query | `/ai why is my build failing?` |
| `/explain` | Explain current state/last result | `/explain` |
| `/explain <file>` | Explain a specific file | `/explain pom.xml` |
| `/review` | AI review of recent changes | `/review` |
| `/review <commit>` | Review specific commit | `/review HEAD~3` |
| `/plan <task>` | Create implementation plan | `/plan add codecov` |
| `/fix` | Suggest fix for last error | `/fix` |
| `/fix <issue>` | Suggest fix for specific issue | `/fix CVE-2024-1234` |
| `/suggest` | AI suggestions for current state | `/suggest` |
| `/diagnose` | Deep diagnosis of failures | `/diagnose` |

### 5.8 Advanced Command Flags

Many commands have sophisticated flag sets that enable powerful workflows:

#### Triage Advanced Flags (Remote Analysis)

| Flag | Purpose | AI Value |
|------|---------|----------|
| `--run RUN_ID` | Analyze specific GitHub workflow run | Fetch remote artifacts |
| `--artifacts-dir PATH` | Use pre-downloaded artifacts (offline) | Offline analysis |
| `--repo OWNER/REPO` | Target remote repository | Cross-repo triage |
| `--workflow NAME` | Filter by workflow name | Targeted analysis |
| `--branch NAME` | Filter by branch | Branch-specific triage |
| `--multi` | Multi-report aggregation mode | Hub-wide view |
| `--aggregate` | Force aggregated output | Combined analysis |
| `--per-repo` | Force per-repo output | Detailed per-repo |
| `--detect-flaky` | Analyze history for flaky patterns | **AI pattern detection** |
| `--gate-history` | Analyze gate status changes | Trend analysis |

#### Check Command Categories

| Flag | What It Runs | AI Value |
|------|--------------|----------|
| `--audit` | Drift detection (links, ADR, configs) | Config drift alerts |
| `--security` | bandit, pip-audit, trivy, gitleaks | Security guidance |
| `--full` | Templates, matrix, license, zizmor | Comprehensive validation |
| `--mutation` | mutmut (~15min) | Mutation analysis |
| `--all` | All of the above | Full audit |
| `--install-missing` | Prompt for missing tools | Auto-setup |
| `--require-optional` | Fail if optional tools missing | Strict mode |

#### CI Command Advanced Features

| Flag | Purpose |
|------|---------|
| `--correlation-id` | Hub correlation tracking |
| `--config-from-hub BASENAME` | Load config from hub's config/repos/ |
| `--write-github-summary` | Write to GITHUB_STEP_SUMMARY |
| `--install-deps` | Install repo dependencies first |

#### Verify Integration Testing

| Flag | Purpose | AI Value |
|------|---------|----------|
| `--remote` | Check connected repos for template drift | Drift detection |
| `--integration` | Clone repos and run cihub ci | Full integration test |
| `--include-disabled` | Include dispatch_enabled=false repos | Comprehensive check |

#### Discover Filtering

| Flag | Purpose |
|------|---------|
| `--run-group {full,smoke,fixtures}` | Filter by run group |
| `--central-only` | Only central runner repos |
| `--dispatch-only` | Only dispatch repos |
| `--github-output` | Write to GITHUB_OUTPUT |

#### Report Dashboard Generation

| Flag | Purpose |
|------|---------|
| `--format {json,html}` | Output format |
| `--schema-mode {warn,strict}` | Schema validation strictness |
| `--include-details` | Include per-repo details |
| `--strict` | Fail if any repo fails |
| `--timeout` | Polling timeout (seconds) |

### 5.9 Interactive Wizard Flags

Commands that support interactive wizard mode:

| Command | Flag | Purpose |
|---------|------|---------|
| `/new <name>` | `--interactive` | Run full wizard |
| `/new <name>` | `--profile PROFILE` | Apply profile template |
| `/init` | `--wizard` | Run init wizard |
| `/config edit` | (default) | Edit via wizard |

### 5.10 Argument Syntax Examples

```bash
# Remote triage with AI pattern detection
/triage --run 12345678 --repo owner/repo --detect-flaky

# Full security and validation audit
/check --all --json

# Integration testing with full CI runs
/verify --integration --repo owner/repo1 --repo owner/repo2

# Hub-wide dashboard generation
/report dashboard --reports-dir ./artifacts --format html --output dashboard.html

# Aggregate with strict mode
/report aggregate --reports-dir ./reports --strict --timeout 3600

# Discover with run group filtering
/discover --run-group smoke,fixtures --central-only

# Init with wizard mode
/init --repo . --wizard

# New repo with profile
/new my-service --profile python-strict --interactive
```

---

## Part 6: AI Enhancement by Category

This section defines **how AI adds value to every command category** - not just basic commands.

### 6.1 Triage Intelligence (HIGHEST ROI)

**The killer feature.** AI interprets CI failures, artifact logs, and test results.

| Capability | Implementation | User Benefit |
|------------|----------------|--------------|
| **Log Interpretation** | AI reads build logs from artifacts | Explains cryptic error messages |
| **Flaky Test Detection** | `--detect-flaky` analyzes history.jsonl | Identifies intermittent failures |
| **Gate History Analysis** | `--gate-history` tracks gate changes | "Coverage dropped from 85% to 72%" |
| **Test Count Regression** | Compares to previous runs | "15 tests were removed" |
| **Root Cause Analysis** | Correlates failures across runs | "This fails when X happens" |
| **Priority Ordering** | AI ranks issues by impact | "Fix A first, then B" |
| **Fix Suggestions** | Context-aware recommendations | "Try adding `--legacy-peer-deps`" |
| **Remote Artifact Fetch** | `--run RUN_ID` fetches from GitHub | Analyze any CI run |
| **Multi-Report Aggregation** | `--multi` combines across repos | Hub-wide health view |

**Built-in Detection Functions (from `cihub/services/triage/detection.py`):**

```python
# Already implemented in Python CLI - TypeScript wraps these
detect_flaky_patterns(history_path, min_runs=5) # Identifies pass/fail oscillation
detect_test_count_regression(history_path, count) # Finds test count drops > 20%
detect_gate_changes(history_path, current_gates) # Tracks threshold violations over time
```

**Evidence Building (from `cihub/services/triage/evidence.py`):**

```python
# Rich artifact parsing
build_tool_evidence(tool, output_dir) # Parses tool-specific outputs
validate_artifact_evidence(evidence) # Validates evidence structure
_load_tool_outputs(output_dir, tool) # Loads pytest, bandit, trivy, etc.
```

**AI Tool Definition for Triage:**

```typescript
const triageTools = [
 {
 name: "analyze_build_log",
 description: "Parse and analyze a CI build log to identify failure patterns",
 input_schema: {
 type: "object",
 properties: {
 log_content: { type: "string", description: "Raw build log content" },
 build_type: { type: "string", enum: ["maven", "gradle", "npm", "pip", "cargo"] }
 },
 required: ["log_content"]
 }
 },
 {
 name: "identify_flaky_tests",
 description: "Analyze test history to identify flaky tests",
 input_schema: {
 type: "object",
 properties: {
 test_results: { type: "array", items: { type: "object" } },
 history_depth: { type: "number", default: 10 }
 },
 required: ["test_results"]
 }
 },
 {
 name: "suggest_fix",
 description: "Suggest a fix for a specific CI failure",
 input_schema: {
 type: "object",
 properties: {
 error_message: { type: "string" },
 context: { type: "object" }
 },
 required: ["error_message"]
 }
 }
];
```

### 6.2 Documentation Intelligence

**AI-driven documentation maintenance** from the DOC_AUTOMATION_AUDIT.md design.

| Capability | Implementation | User Benefit |
|------------|----------------|--------------|
| **Stale Doc Detection** | Python AST + git diff analysis | Find outdated docs automatically |
| **Change Mapping** | Link code changes to docs | "This function changed, update docs" |
| **Auto-Generation** | Generate docs from code | CLI reference from argparse |
| **Prompt Pack** | `--ai` flag outputs markdown | Pass directly to AI for updates |

**AI Prompt Pack Pattern:**

```typescript
// When user runs: /docs stale --ai
async function docsStaleWithAI(cwd: string): Promise<void> {
 // 1. Run Python CLI to get stale doc analysis
 const result = await runCihub("docs", ["stale", "--ai"], cwd);

 // 2. Extract AI prompt pack from result
 const promptPack = result.data?.ai_prompt_pack;

 // 3. Pass to AI for suggested updates
 const suggestions = await runAI(promptPack, {
 systemPrompt: `You are a documentation updater. Suggest specific edits
 to bring documentation in sync with code changes.`
 });

 // 4. Display suggestions with apply option
 displaySuggestions(suggestions);
}
```

### 6.3 Report Translation

**AI explains reports in natural language.**

| Report Type | AI Capability |
|-------------|---------------|
| **Summary** | "Your build health is declining; failures up 20% this week" |
| **Security** | "CVE-2024-1234 is critical; affects auth module; patch available" |
| **Coverage** | "Coverage dropped in `auth.py`; 3 new functions untested" |
| **Performance** | "Build time increased 2x; likely due to new dependency" |

**Implementation:**

```typescript
async function explainReport(reportType: string, cwd: string): Promise<string> {
 // Get raw report data
 const report = await runCihub("report", [reportType], cwd);

 // AI interprets the data
 const explanation = await runAI(`
 Explain this CI report in plain English. Highlight:
 1. Key findings
 2. What needs attention
 3. Recommended actions

 Report data:
 ${JSON.stringify(report, null, 2)}
 `, { model: "claude-3-haiku-20240307" }); // Fast model for explanations

 return explanation;
}
```

### 6.4 Error Diagnosis

**AI helps with cryptic CI/build errors.**

| Error Type | AI Assistance |
|------------|---------------|
| **Maven/Gradle** | Decode dependency conflicts, plugin version issues |
| **npm/pnpm** | Explain peer dependency errors, lockfile conflicts |
| **Python** | Interpret pip resolver failures, version conflicts |
| **Docker** | Explain build failures, layer caching issues |
| **GitHub Actions** | Decode runner errors, permission issues |

**Diagnostic Flow:**

```
User: /diagnose

AI: [Analyzes last command result and any artifacts]

Output:
┌─────────────────────────────────────────────────────────────┐
│ Diagnosis: Maven Dependency Conflict │
├─────────────────────────────────────────────────────────────┤
│ │
│ Problem: jackson-databind versions clash │
│ │
│ spring-boot-starter: requires 2.15.2 │
│ aws-sdk-java: requires 2.12.0 │
│ │
│ Root Cause: │
│ The aws-sdk brings an older jackson version that conflicts │
│ with Spring Boot's managed version. │
│ │
│ Suggested Fix: │
│ Add to pom.xml <dependencyManagement>: │
│ <dependency> │
│ <groupId>com.fasterxml.jackson.core</groupId> │
│ <artifactId>jackson-databind</artifactId> │
│ <version>2.15.2</version> │
│ </dependency> │
│ │
│ Run `/fix --apply` to apply this suggestion. │
└─────────────────────────────────────────────────────────────┘
```

### 6.5 Configuration Advisor

**AI optimizes cihub and CI configurations.**

| Config Type | AI Capability |
|-------------|---------------|
| **cihub.yaml** | Suggest optimal settings for project type |
| **GitHub Actions** | Optimize workflow for faster builds |
| **pom.xml** | Recommend plugin versions, configurations |
| **package.json** | Script optimization, dependency updates |

**Example Interaction:**

```
User: /ai how can I speed up my CI?

AI: [Analyzes current configuration]

Based on your project, here are optimization suggestions:

1. **Enable dependency caching** (saves ~2 min)
 Your workflow doesn't cache Maven dependencies.
 Run: /hub-ci add-cache maven

2. **Parallelize test suites** (saves ~5 min)
 You have 3 test modules running sequentially.
 Run: /hub-ci matrix-tests

3. **Skip redundant steps** (saves ~1 min)
 Coverage runs on every push; consider PR-only.
 Run: /hub-ci optimize-triggers

Estimated time savings: 8 minutes per build
Apply all? [Y/n]
```

### 6.6 Security Intelligence

**AI-assisted security issue handling.**

| Capability | Implementation |
|------------|----------------|
| **CVE Explanation** | Plain-English description of vulnerability |
| **Impact Assessment** | "This affects your auth module's login flow" |
| **Patch Guidance** | Step-by-step remediation instructions |
| **False Positive ID** | Identify likely false positives |

### 6.8 Gate Specifications System

The Python CLI uses a declarative **GateSpec** system for quality gates. The TypeScript CLI can leverage this for intelligent threshold recommendations:

**Gate Threshold Types (from `cihub/core/gate_specs.py`):**

| Threshold | Comparator | Purpose |
|-----------|------------|---------|
| `coverage_min` | GTE | Minimum code coverage % |
| `mutation_score_min` | GTE | Minimum mutation score % |
| `trivy_cvss_fail` | CVSS | Max CVSS score before fail |
| `max_critical_vulns` | LTE | Max critical vulnerabilities |
| `max_high_vulns` | LTE | Max high vulnerabilities |
| `max_bandit_high` | LTE | Max high-severity bandit issues |
| `max_pip_audit_vulns` | LTE | Max pip-audit vulnerabilities |

**AI Gate Advisor:**

```typescript
// AI can recommend thresholds based on project characteristics
async function recommendThresholds(projectInfo: ProjectInfo): Promise<ThresholdRecommendation> {
 const prompt = `
 Project type: ${projectInfo.type}
 Current coverage: ${projectInfo.currentCoverage}%
 Security stance: ${projectInfo.securityLevel}
 Team size: ${projectInfo.teamSize}

 Recommend appropriate CI quality gate thresholds.
 Consider: project maturity, risk tolerance, industry standards.
 `;
 return await runAI(prompt);
}
```

### 6.9 Language Strategy Pattern

The CLI supports Python and Java with polymorphic language handling. AI can help with language-specific issues:

| Language | Tools | AI Assistance |
|----------|-------|---------------|
| **Python** | pytest, ruff, black, mypy, bandit, pip-audit, mutmut, trivy | Dependency resolution, import errors |
| **Java** | maven/gradle, junit, jacoco, checkstyle, spotbugs, owasp | POM fixes, classpath issues |

**Future Languages (Strategy Pattern enables easy addition):**

| Language | Potential Tools | Status |
|----------|-----------------|--------|
| Go | go test, golint, govulncheck | Planned |
| Rust | cargo test, clippy, cargo-audit | Planned |
| TypeScript | jest/vitest, eslint, npm audit | Planned |

### 6.7 Project Setup Wizard

**AI guides new project initialization.**

```
User: /init

AI: I'll help you set up cihub for this project.

Detected: Python project (pyproject.toml found)
 Git repository (main branch)
 GitHub remote (owner/repo)

Recommended configuration:
┌───────────────────────────────────────────┐
│ language: python │
│ python: │
│ version: "3.11" │
│ test_command: "pytest" │
│ lint_command: "ruff check" │
│ coverage_threshold: 80 │
│ ci: │
│ provider: github │
│ workflow: .github/workflows/ci.yml │
└───────────────────────────────────────────┘

Create this configuration? [Y/n]
```

---

## Part 7: Hub-CI Subcommands (46 Tools)

The `hub-ci` command provides 46 specialized CI/CD tools. Each maps to a slash command.

### 7.1 Validation Tools (11 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci check-workflows` | Validate GitHub workflow YAML | Suggest fixes |
| `/hub-ci check-renovate` | Validate renovate.json | Config optimization |
| `/hub-ci check-pr` | Validate PR requirements | PR improvement tips |
| `/hub-ci check-smoke` | Validate smoke test configs | Test suggestions |
| `/hub-ci check-codeowners` | Validate CODEOWNERS file | Coverage gaps |
| `/hub-ci check-branch-protection` | Check branch rules | Security recommendations |
| `/hub-ci check-secrets` | Validate secret configuration | Security audit |
| `/hub-ci check-required-files` | Check for required files | Missing file suggestions |
| `/hub-ci check-labels` | Validate PR labels | Label scheme optimization |
| `/hub-ci check-issue-templates` | Validate issue templates | Template improvements |
| `/hub-ci check-all` | Run all validation checks | Comprehensive report |

### 7.2 Security Tools (8 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci security-scan` | Run security scanners | Vulnerability explanations |
| `/hub-ci dependency-audit` | Audit dependencies | Upgrade recommendations |
| `/hub-ci license-check` | Check license compliance | Compliance guidance |
| `/hub-ci secrets-scan` | Scan for leaked secrets | Remediation steps |
| `/hub-ci container-scan` | Scan container images | Image hardening tips |
| `/hub-ci sast` | Static analysis | Code fix suggestions |
| `/hub-ci supply-chain` | Check supply chain | SBOM generation |
| `/hub-ci security-report` | Generate security report | Executive summary |

### 7.3 Smoke Test Tools (5 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci smoke-setup` | Set up smoke tests | Config generation |
| `/hub-ci smoke-run` | Run smoke tests | Failure diagnosis |
| `/hub-ci smoke-validate` | Validate smoke configs | Config fixes |
| `/hub-ci smoke-report` | Generate smoke report | Test insights |
| `/hub-ci smoke-optimize` | Optimize smoke tests | Performance tips |

### 7.4 Python Tools (6 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci python-check` | Run Python checks | Fix suggestions |
| `/hub-ci python-coverage` | Check Python coverage | Coverage gaps |
| `/hub-ci python-deps` | Manage Python deps | Upgrade recommendations |
| `/hub-ci python-lint` | Run Python linters | Auto-fix application |
| `/hub-ci python-test` | Run Python tests | Failure diagnosis |
| `/hub-ci python-type` | Run type checking | Type error fixes |

### 7.5 Java Tools (6 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci java-check` | Run Java checks | Fix suggestions |
| `/hub-ci java-coverage` | Check Java coverage | Coverage gaps |
| `/hub-ci java-deps` | Manage Java deps | Dependency analysis |
| `/hub-ci java-lint` | Run Java linters | Checkstyle fixes |
| `/hub-ci java-test` | Run Java tests | Test failure diagnosis |
| `/hub-ci pom-analyze` | Analyze pom.xml | POM optimization |

### 7.6 Release Tools (5 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci release-prepare` | Prepare release | Release notes draft |
| `/hub-ci release-publish` | Publish release | Publish verification |
| `/hub-ci version-bump` | Bump version | Semantic version advice |
| `/hub-ci changelog` | Generate changelog | Changelog writing |
| `/hub-ci tag` | Create git tag | Tag naming |

### 7.7 Badge Tools (3 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci update-badges` | Update README badges | Badge suggestions |
| `/hub-ci badge-status` | Check badge status | Badge troubleshooting |
| `/hub-ci badge-generate` | Generate badge URLs | Badge customization |

### 7.8 Utility Tools (2 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/hub-ci status` | Overall hub-ci status | Health interpretation |
| `/hub-ci doctor` | Diagnose issues | Problem resolution |

### 7.9 Dispatch Subcommands (2 Commands)

| Slash Command | Purpose | AI Enhancement |
|---------------|---------|----------------|
| `/dispatch trigger` | Dispatch workflow and poll for run ID | Workflow selection help |
| `/dispatch metadata` | Generate dispatch metadata JSON | Metadata generation |

---

## Part 8: Interactive Wizard System

The CIHub CLI includes a full **interactive wizard system** for onboarding repos. This MUST be replicated in the TypeScript CLI.

### 8.1 Wizard Entry Points

| Command | Purpose | Wizard Type |
|---------|---------|-------------|
| `/new <repo>` | Create hub-side repo config | `run_new_wizard()` |
| `/init` | Initialize repo with detection | `run_init_wizard()` |
| `/config edit` | Edit existing config | `run_config_wizard()` |

### 8.2 Wizard Flow

The wizard guides users through:

```
┌─────────────────────────────────────────────────────────────────┐
│ CIHub New Repo Wizard │
├─────────────────────────────────────────────────────────────────┤
│ │
│ Step 1: Repository Details │
│ ───────────────────────────────────────────────────── │
│ ? Repo owner (org/user): jguida941 │
│ ? Repo name: my-awesome-app │
│ ? Use central runner? (Y/n): Y │
│ ? Enable repo-side execution? (y/N): N │
│ │
│ Step 2: Language Selection │
│ ───────────────────────────────────────────────────── │
│ ? Select language: │
│ java │
│ python │
│ │
│ Step 3: Python Configuration (if python) │
│ ───────────────────────────────────────────────────── │
│ ? Python version: 3.12 │
│ │
│ Step 4: Tool Selection (yes/no for each) │
│ ───────────────────────────────────────────────────── │
│ ? Enable pytest? (Y/n): Y │
│ ? Enable ruff? (Y/n): Y │
│ ? Enable black? (Y/n): Y │
│ ? Enable isort? (y/N): N │
│ ? Enable mypy? (y/N): Y │
│ ? Enable bandit? (Y/n): Y │
│ ? Enable pip-audit? (Y/n): Y │
│ ? Enable mutmut? (y/N): N │
│ ? Enable hypothesis? (y/N): N │
│ ? Enable semgrep? (y/N): N │
│ ? Enable trivy? (Y/n): Y │
│ ? Enable codeql? (y/N): N │
│ ? Enable docker? (y/N): N │
│ │
│ Step 5: Security Tools │
│ ───────────────────────────────────────────────────── │
│ ? Enable OWASP dependency check? (Y/n): Y │
│ ? Enable gitleaks? (Y/n): Y │
│ │
│ Step 6: Thresholds │
│ ───────────────────────────────────────────────────── │
│ ? Coverage threshold (%): 80 │
│ ? Max allowed security vulnerabilities: 0 │
│ │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Python Tools Available

| Tool | Default | Purpose |
|------|---------|---------|
| pytest | enabled | Test runner |
| ruff | enabled | Fast linter |
| black | enabled | Code formatter |
| isort | disabled | Import sorter |
| mypy | disabled | Type checker |
| bandit | enabled | Security scanner |
| pip_audit | enabled | Dependency audit |
| mutmut | disabled | Mutation testing |
| hypothesis | disabled | Property testing |
| semgrep | disabled | SAST scanner |
| trivy | enabled | Container scanner |
| codeql | disabled | Code analysis |
| docker | disabled | Docker builds |

### 8.4 Java Tools Available

| Tool | Default | Purpose |
|------|---------|---------|
| maven/gradle | required | Build tool |
| junit | enabled | Test runner |
| jacoco | enabled | Coverage |
| checkstyle | enabled | Style checker |
| spotbugs | disabled | Bug finder |
| owasp | enabled | Dependency check |
| codeql | disabled | Code analysis |
| docker | disabled | Docker builds |

### 8.5 Profile System

Profiles allow pre-configured tool settings to be applied during setup:

```bash
# Apply a profile during new repo creation
/new my-service --profile python-strict

# Profiles are stored in templates/profiles/*.yaml
```

**Profile Example (`python-strict.yaml`):**

```yaml
language: python
python:
 version: "3.12"
 tools:
 pytest:
 enabled: true
 ruff:
 enabled: true
 black:
 enabled: true
 mypy:
 enabled: true
 bandit:
 enabled: true
 pip_audit:
 enabled: true
 mutmut:
 enabled: true
thresholds:
 coverage_min: 90
 mutation_score_min: 80
```

**Profile Commands:**

| Command | Purpose |
|---------|---------|
| `/new <repo> --profile <name>` | Apply profile to new repo |
| `/config apply-profile --repo <repo> --profile <name>` | Apply profile to existing repo |
| `/hub-ci validate-profiles` | Validate all profile YAML files |

### 8.6 TypeScript Wizard Implementation

The TypeScript CLI must replicate this wizard using **Ink select/confirm components**:

```typescript
// src/components/Wizard.tsx
import React, { useState } from "react";
import { Box, Text } from "ink";
import SelectInput from "ink-select-input";
import ConfirmInput from "@inkjs/ui/confirm-input";
import TextInput from "ink-text-input";

interface WizardStep {
 type: "text" | "select" | "confirm";
 question: string;
 key: string;
 default?: string | boolean;
 choices?: string[];
}

const WIZARD_STEPS: WizardStep[] = [
 // Step 1: Repo details
 { type: "text", question: "Repo owner (org/user):", key: "repo.owner" },
 { type: "text", question: "Repo name:", key: "repo.name" },
 { type: "confirm", question: "Use central runner?", key: "repo.use_central_runner", default: true },
 { type: "confirm", question: "Enable repo-side execution?", key: "repo.repo_side_execution", default: false },

 // Step 2: Language
 { type: "select", question: "Select language:", key: "language", choices: ["java", "python"] },

 // Python tools (shown if language === "python")
 { type: "text", question: "Python version:", key: "python.version", default: "3.12" },
 { type: "confirm", question: "Enable pytest?", key: "python.tools.pytest.enabled", default: true },
 { type: "confirm", question: "Enable ruff?", key: "python.tools.ruff.enabled", default: true },
 { type: "confirm", question: "Enable black?", key: "python.tools.black.enabled", default: true },
 { type: "confirm", question: "Enable mypy?", key: "python.tools.mypy.enabled", default: false },
 { type: "confirm", question: "Enable bandit?", key: "python.tools.bandit.enabled", default: true },
 { type: "confirm", question: "Enable pip-audit?", key: "python.tools.pip_audit.enabled", default: true },
 { type: "confirm", question: "Enable mutmut?", key: "python.tools.mutmut.enabled", default: false },
 { type: "confirm", question: "Enable trivy?", key: "python.tools.trivy.enabled", default: true },
 // ... more tools

 // Thresholds
 { type: "text", question: "Coverage threshold (%):", key: "thresholds.coverage", default: "80" },
];

export function NewRepoWizard({ onComplete }: { onComplete: (config: object) => void }) {
 const [step, setStep] = useState(0);
 const [config, setConfig] = useState({});

 const currentStep = WIZARD_STEPS[step];

 const handleAnswer = (value: string | boolean) => {
 // Update config using lodash.set or similar
 const newConfig = { ...config };
 setDeep(newConfig, currentStep.key, value);
 setConfig(newConfig);

 if (step < WIZARD_STEPS.length - 1) {
 setStep(step + 1);
 } else {
 onComplete(newConfig);
 }
 };

 return (
 <Box flexDirection="column">
 <Text bold>Step {step + 1} of {WIZARD_STEPS.length}</Text>
 <Text>{currentStep.question}</Text>

 {currentStep.type === "confirm" && (
 <ConfirmInput
 defaultChoice={currentStep.default as boolean}
 onConfirm={() => handleAnswer(true)}
 onCancel={() => handleAnswer(false)}
 />
 )}

 {currentStep.type === "select" && (
 <SelectInput
 items={currentStep.choices!.map(c => ({ label: c, value: c }))}
 onSelect={item => handleAnswer(item.value)}
 />
 )}

 {currentStep.type === "text" && (
 <TextInput
 value=""
 onChange={() => {}}
 onSubmit={handleAnswer}
 placeholder={currentStep.default as string}
 />
 )}
 </Box>
 );
}
```

### 8.7 AI-Enhanced Wizard

The TypeScript CLI can enhance the wizard with AI recommendations:

```typescript
// AI provides recommendations during wizard
async function getAIRecommendations(
 detected: DetectedConfig,
 step: string
): Promise<WizardSuggestion> {
 const prompt = `
 Given this detected project configuration:
 ${JSON.stringify(detected, null, 2)}

 What should the user enable for: ${step}?
 Consider: project size, existing tools, best practices.
 `;

 return await runAI(prompt, { model: "claude-3-haiku-20240307" });
}

// During wizard:
// "AI recommends: Enable ruff and black for this Python project (detected pyproject.toml)"
```

---

## Part 9: Modular AI Architecture (Python)

**Key Principle:** AI integration lives in the **Python CLI** as a modular, self-contained package. The TypeScript CLI simply passes `--ai` flags through and displays results. This keeps AI logic in one place and maintains separation of concerns.

### 9.1 Directory Structure

```
cihub/
├── ai/ # NEW: Modular AI package
│ ├── __init__.py # Public API exports
│ ├── claude_client.py # Claude CLI subprocess wrapper
│ ├── context.py # Context builder for AI prompts
│ ├── enhance.py # Result enhancement logic
│ └── providers/ # Future: Multiple AI providers
│ ├── __init__.py
│ ├── base.py # Abstract provider interface
│ └── claude.py # Claude implementation
├── commands/ # Existing commands (unchanged)
├── services/ # Existing services (unchanged)
└── ...
```

### 9.2 Public API (`cihub/ai/__init__.py`)

```python
"""CIHub AI Enhancement Module.

This module provides optional AI enhancement for CLI commands.
AI is NEVER required - commands work fully without it.

Usage:
 from cihub.ai import enhance_result, is_ai_available

 result = cmd_triage(args)
 if args.ai and is_ai_available():
 result = enhance_result(result, context)
"""

from cihub.ai.enhance import enhance_result
from cihub.ai.context import build_context
from cihub.ai.claude_client import is_ai_available, invoke_claude

__all__ = [
 "enhance_result",
 "build_context",
 "is_ai_available",
 "invoke_claude",
]
```

### 9.3 Claude Client (`cihub/ai/claude_client.py`)

```python
"""Claude CLI subprocess wrapper.

Calls Claude Code in headless mode (-p) for AI analysis.
Falls back gracefully if Claude is not installed.
"""

from __future__ import annotations

import json
import subprocess
import shutil
from typing import Any

# Timeout for AI calls (seconds)
AI_TIMEOUT = 60


def is_ai_available() -> bool:
 """Check if Claude CLI is available."""
 return shutil.which("claude") is not None


def invoke_claude(
 prompt: str,
 *,
 output_format: str = "json",
 timeout: int = AI_TIMEOUT,
) -> dict[str, Any] | None:
 """Invoke Claude Code in headless mode.

 Args:
 prompt: The prompt to send to Claude.
 output_format: Output format ("json" or "text").
 timeout: Timeout in seconds.

 Returns:
 Parsed JSON response, or None if failed.
 """
 if not is_ai_available():
 return None

 try:
 result = subprocess.run(
 ["claude", "-p", prompt, "--output-format", output_format],
 capture_output=True,
 text=True,
 timeout=timeout,
 )

 if result.returncode != 0:
 return None

 if output_format == "json":
 return json.loads(result.stdout)
 return {"result": result.stdout}

 except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
 return None
```

### 9.4 Context Builder (`cihub/ai/context.py`)

```python
"""Build structured context for AI prompts.

Instead of AI searching files, we provide all context upfront.
This makes AI faster and more accurate.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
 from cihub.types import CommandResult

# Import existing registries (no duplication!)
from cihub.services.triage.types import (
 CATEGORY_BY_TOOL,
 SEVERITY_BY_CATEGORY,
)


def build_context(
 result: "CommandResult",
 *,
 include_tool_registry: bool = True,
 include_suggestions: bool = True,
) -> str:
 """Build structured context string for AI.

 Args:
 result: The CommandResult to analyze.
 include_tool_registry: Include tool categorization info.
 include_suggestions: Include existing suggestions.

 Returns:
 Formatted context string for AI prompt.
 """
 sections = []

 # Command result summary
 sections.append(f"""## Command Result
- Command: {result.artifacts.get('command', 'unknown')}
- Exit Code: {result.exit_code}
- Summary: {result.summary}
""")

 # Problems (if any)
 if result.problems:
 problems_text = json.dumps(result.problems, indent=2)
 sections.append(f"""## Problems Found
```json
{problems_text}
```
""")

 # Tool registry (helps AI understand categorization)
 if include_tool_registry:
 sections.append(f"""## Tool Categorization (Reference)
Categories: {json.dumps(CATEGORY_BY_TOOL, indent=2)}
Severity Mapping: {json.dumps(SEVERITY_BY_CATEGORY, indent=2)}
""")

 # Existing suggestions
 if include_suggestions and result.suggestions:
 suggestions_text = "\n".join(
 f"- {s.get('message', '')}" for s in result.suggestions
 )
 sections.append(f"""## Existing Suggestions
{suggestions_text}
""")

 return "\n".join(sections)
```

### 9.5 Result Enhancement (`cihub/ai/enhance.py`)

```python
"""Enhance CommandResult with AI analysis.

This is the main entry point for AI enhancement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cihub.ai.claude_client import invoke_claude, is_ai_available
from cihub.ai.context import build_context

if TYPE_CHECKING:
 from cihub.types import CommandResult


def enhance_result(
 result: "CommandResult",
 *,
 mode: str = "analyze",
) -> "CommandResult":
 """Enhance a CommandResult with AI analysis.

 Args:
 result: The CommandResult to enhance.
 mode: Enhancement mode ("analyze", "fix", "explain").

 Returns:
 Enhanced CommandResult with AI suggestions added.
 """
 if not is_ai_available():
 result.suggestions.append({
 "message": "AI enhancement unavailable (Claude CLI not found)",
 "source": "cihub",
 })
 return result

 # Build context from result
 context = build_context(result)

 # Build prompt based on mode
 if mode == "analyze":
 prompt = f"""Analyze this CI/CD failure and suggest fixes.

{context}

Provide:
1. Root cause (1 sentence)
2. Specific fix steps (numbered list)
3. Prevention tip (1 sentence)

Be concise and actionable."""

 elif mode == "explain":
 prompt = f"""Explain this CI/CD result in plain language.

{context}

Explain what happened and what the user should do next.
Use simple language, no jargon."""

 elif mode == "fix":
 prompt = f"""Suggest specific code/config fixes for these issues.

{context}

For each problem, provide the exact fix (file path, line, change)."""

 else:
 prompt = f"Analyze: {context}"

 # Invoke Claude
 response = invoke_claude(prompt)

 if response and "result" in response:
 result.data["ai_analysis"] = response["result"]
 result.suggestions.append({
 "message": response["result"],
 "source": "claude",
 "mode": mode,
 })

 return result
```

### 9.6 Integration with Commands

Commands opt-in to AI enhancement with minimal changes:

```python
# In cihub/commands/triage.py

def cmd_triage(args: argparse.Namespace) -> int | CommandResult:
 # ... existing triage logic (unchanged) ...
 result = build_triage_result()

 # NEW: Optional AI enhancement (3 lines added)
 if getattr(args, "ai", False):
 from cihub.ai import enhance_result
 result = enhance_result(result, mode="analyze")

 return result
```

### 9.7 CLI Flag Addition

Add `--ai` flag to the argument parser:

```python
# In cihub/cli_parsers/builder.py

def _add_common_flags(parser: argparse.ArgumentParser) -> None:
 """Add flags common to multiple commands."""
 parser.add_argument(
 "--ai",
 action="store_true",
 default=False,
 help="Enable AI-assisted analysis (requires Claude CLI)",
 )
 parser.add_argument(
 "--no-ai",
 action="store_false",
 dest="ai",
 help="Disable AI assistance",
 )
```

### 9.8 Dev Mode Environment Variable

For developers debugging the CLI itself:

```python
# In cihub/cli.py main()

import os

def main(argv: list[str] | None = None) -> int:
 # ... existing code ...

 result = args.func(args)

 # Dev mode: auto-invoke AI on failures
 if (
 os.getenv("CIHUB_DEV_MODE")
 and isinstance(result, CommandResult)
 and result.exit_code != 0
 ):
 from cihub.ai import enhance_result, is_ai_available
 if is_ai_available():
 print("[DEV MODE] Invoking AI for debugging...", file=sys.stderr)
 result = enhance_result(result, mode="analyze")

 # ... rest of main() ...
```

### 9.9 TypeScript CLI: AI Comes Free

Because AI runs at the Python level, TypeScript just passes flags:

```typescript
// In TypeScript CLI - no AI-specific code needed!
async function runCommand(cmd: string, args: string[], useAI: boolean): Promise<CommandResult> {
 const finalArgs = useAI ? [...args, "--ai"] : args;
 return runCihub(cmd, finalArgs, cwd);
}
```

### 9.10 Testing the AI Module

```python
# tests/test_ai_module.py

import pytest
from unittest.mock import patch, MagicMock

from cihub.ai import enhance_result, is_ai_available, build_context
from cihub.types import CommandResult


class TestAIModule:
 """Tests for the modular AI package."""

 def test_is_ai_available_no_claude(self):
 """AI unavailable when Claude not installed."""
 with patch("shutil.which", return_value=None):
 assert is_ai_available() is False

 def test_is_ai_available_with_claude(self):
 """AI available when Claude is installed."""
 with patch("shutil.which", return_value="/usr/bin/claude"):
 assert is_ai_available() is True

 def test_build_context_includes_problems(self):
 """Context includes problems from result."""
 result = CommandResult(
 exit_code=1,
 summary="Check failed",
 problems=[{"severity": "error", "message": "Ruff found 5 errors"}],
 )
 context = build_context(result)
 assert "Ruff found 5 errors" in context
 assert "error" in context

 def test_enhance_result_without_claude(self):
 """Enhancement gracefully handles missing Claude."""
 result = CommandResult(exit_code=1, summary="Failed")

 with patch("cihub.ai.enhance.is_ai_available", return_value=False):
 enhanced = enhance_result(result)

 assert any("unavailable" in s.get("message", "") for s in enhanced.suggestions)

 def test_enhance_result_with_claude(self):
 """Enhancement adds AI suggestions when Claude available."""
 result = CommandResult(exit_code=1, summary="Failed")
 mock_response = {"result": "Try running ruff --fix"}

 with patch("cihub.ai.enhance.is_ai_available", return_value=True):
 with patch("cihub.ai.enhance.invoke_claude", return_value=mock_response):
 enhanced = enhance_result(result)

 assert any("ruff --fix" in s.get("message", "") for s in enhanced.suggestions)
 assert enhanced.data.get("ai_analysis") == "Try running ruff --fix"


class TestClaudeClient:
 """Tests for Claude subprocess wrapper."""

 def test_invoke_claude_timeout(self):
 """Handles timeout gracefully."""
 from cihub.ai.claude_client import invoke_claude

 with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 60)):
 result = invoke_claude("test prompt")

 assert result is None

 def test_invoke_claude_not_installed(self):
 """Handles missing Claude gracefully."""
 from cihub.ai.claude_client import invoke_claude

 with patch("shutil.which", return_value=None):
 result = invoke_claude("test prompt")

 assert result is None
```

### 9.11 Why This Architecture?

| Principle | Implementation |
|-----------|----------------|
| **Separation of Concerns** | AI logic isolated in `cihub/ai/` |
| **Composition over Inheritance** | Commands call `enhance_result()`, don't extend AI classes |
| **Optional by Default** | `--ai` flag, everything works without it |
| **No Duplication** | Uses existing registries (`CATEGORY_BY_TOOL`, etc.) |
| **Testable** | Mock `invoke_claude()` to test enhancement logic |
| **Provider Agnostic** | `providers/` directory ready for OpenAI, local LLMs |
| **TypeScript Gets It Free** | Just passes `--ai` flag to Python |

### 9.12 Future: Multiple Providers

The `providers/` directory is ready for expansion:

```python
# cihub/ai/providers/base.py
from abc import ABC, abstractmethod

class AIProvider(ABC):
 """Abstract base class for AI providers."""

 @abstractmethod
 def is_available(self) -> bool:
 """Check if provider is available."""
 pass

 @abstractmethod
 def invoke(self, prompt: str, **kwargs) -> dict | None:
 """Invoke the AI provider."""
 pass

# cihub/ai/providers/claude.py
class ClaudeProvider(AIProvider):
 """Claude CLI provider."""
 # ... implementation ...

# cihub/ai/providers/openai.py (future)
class OpenAIProvider(AIProvider):
 """OpenAI API provider."""
 # ... implementation ...
```

Select provider via environment variable:

```bash
# Use Claude (default)
cihub triage --ai

# Use OpenAI (future)
CIHUB_AI_PROVIDER=openai cihub triage --ai
```

---

## Legacy Section: AI Integration Architecture (Deprecated)

> **Note:** The following section is kept for reference but superseded by Part 9 above.
> The simpler approach uses subprocess calls to Claude CLI rather than embedding
> the Anthropic SDK directly in TypeScript.

### 9.2 AI Tool Definitions (Legacy)

The AI assistant has access to these tools for executing cihub commands:

```typescript
// src/lib/ai-tools.ts

export const cihubTools = [
 {
 name: "run_cihub",
 description: "Execute any CIHub CLI command and return structured results",
 input_schema: {
 type: "object",
 properties: {
 command: {
 type: "string",
 description: "The cihub command (e.g., 'discover', 'triage', 'hub-ci check-workflows')"
 },
 args: {
 type: "array",
 items: { type: "string" },
 description: "Command arguments and flags"
 }
 },
 required: ["command"]
 }
 },
 {
 name: "read_artifact",
 description: "Read and analyze a CI artifact file (logs, test results, etc.)",
 input_schema: {
 type: "object",
 properties: {
 path: { type: "string", description: "Path to the artifact file" },
 artifact_type: {
 type: "string",
 enum: ["build_log", "test_results", "coverage", "security_scan"],
 description: "Type of artifact for specialized parsing"
 }
 },
 required: ["path"]
 }
 },
 {
 name: "suggest_fix",
 description: "Generate a fix suggestion for a specific issue",
 input_schema: {
 type: "object",
 properties: {
 issue_type: { type: "string" },
 error_message: { type: "string" },
 file_path: { type: "string" },
 context: { type: "object" }
 },
 required: ["issue_type", "error_message"]
 }
 },
 {
 name: "apply_fix",
 description: "Apply a suggested fix (requires user confirmation)",
 input_schema: {
 type: "object",
 properties: {
 fix_id: { type: "string" },
 file_path: { type: "string" },
 changes: { type: "array", items: { type: "object" } }
 },
 required: ["fix_id", "file_path", "changes"]
 }
 }
];
```

### 9.3 AI Client Implementation

```typescript
// src/lib/ai-client.ts
import Anthropic from "@anthropic-ai/sdk";
import { cihubTools } from "./ai-tools.js";
import { runCihub } from "./cihub.js";

interface AIContext {
 cwd: string;
 language: string;
 lastResult?: CommandResult;
 projectConfig?: object;
}

export async function runAI(
 prompt: string,
 context: AIContext,
 options: { stream?: boolean } = {}
): Promise<string> {
 const client = new Anthropic();

 const systemPrompt = `You are a CI/CD assistant integrated into CIHub.
You help users understand and fix CI/CD issues.

Context:
- Working directory: ${context.cwd}
- Project language: ${context.language}
- Last command result: ${context.lastResult ? JSON.stringify(context.lastResult.summary) : "None"}

You can run cihub commands to gather information or fix issues.
Always explain what you're doing and why.`;

 const response = await client.messages.create({
 model: "claude-sonnet-4-20250514",
 max_tokens: 4096,
 system: systemPrompt,
 tools: cihubTools,
 messages: [{ role: "user", content: prompt }],
 });

 // Handle tool calls in a loop
 let messages = [{ role: "user", content: prompt }];
 let currentResponse = response;

 while (currentResponse.stop_reason === "tool_use") {
 const toolUse = currentResponse.content.find(c => c.type === "tool_use");

 // Execute the tool
 let toolResult: string;
 if (toolUse.name === "run_cihub") {
 const result = await runCihub(
 toolUse.input.command,
 toolUse.input.args || [],
 context.cwd
 );
 toolResult = JSON.stringify(result);
 } else if (toolUse.name === "read_artifact") {
 toolResult = await readArtifact(toolUse.input.path, toolUse.input.artifact_type);
 } else {
 toolResult = `Unknown tool: ${toolUse.name}`;
 }

 // Continue conversation with tool result
 messages.push(
 { role: "assistant", content: currentResponse.content },
 { role: "user", content: [{ type: "tool_result", tool_use_id: toolUse.id, content: toolResult }] }
 );

 currentResponse = await client.messages.create({
 model: "claude-sonnet-4-20250514",
 max_tokens: 4096,
 system: systemPrompt,
 tools: cihubTools,
 messages,
 });
 }

 // Extract text response
 const textContent = currentResponse.content.find(c => c.type === "text");
 return textContent?.text || "";
}
```

### 9.4 Safety Boundaries

| Boundary | Implementation | Rationale |
|----------|----------------|-----------|
| **Command allowlist** | AI can only run `cihub` commands | No arbitrary shell execution |
| **Dry-run default** | `--apply` required for modifications | Preview before apply |
| **Confirmation UI** | File writes require user confirmation | User remains in control |
| **Context limits** | AI sees config/results, not full code | Reduces token usage, improves focus |
| **Rate limiting** | Max 10 tool calls per interaction | Prevents runaway loops |
| **Audit logging** | All AI actions logged | Traceability |

### 9.5 Streaming Responses

For long AI responses, stream to terminal in real-time:

```typescript
// src/lib/ai-stream.ts
export async function* streamAI(
 prompt: string,
 context: AIContext
): AsyncGenerator<string> {
 const client = new Anthropic();

 const stream = await client.messages.stream({
 model: "claude-sonnet-4-20250514",
 max_tokens: 4096,
 system: buildSystemPrompt(context),
 messages: [{ role: "user", content: prompt }],
 });

 for await (const event of stream) {
 if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
 yield event.delta.text;
 }
 }
}
```

---

## Part 10: Blockers & Prerequisites

### 10.1 Critical: JSON Output Purity

**Problem:** 80 print statements across 18 files can corrupt JSON output.

**Files emitting GitHub annotations in stdout:**
- `smoke.py` - `::warning::`
- `report/validate.py` - `::warning::`
- `discover.py` - `::warning::`

**Fix Required:**
```python
# BEFORE (breaks JSON parsing)
print("::warning::Something happened")

# AFTER (clean JSON on stdout)
if json_mode:
 # Include in CommandResult.problems instead
 problems.append({"severity": "warning", "message": "Something happened"})
else:
 print("::warning::Something happened", file=sys.stderr)
```

**Contract Test:**
```typescript
// test/json-purity.test.ts
test.each(ALL_COMMANDS)("%s returns valid JSON", async (cmd) => {
 const { stdout } = await execa("cihub", [cmd, "--json"]);
 expect(() => JSON.parse(stdout)).not.toThrow();
});
```

### 10.2 Required: Python CLI Available

The TypeScript CLI spawns the Python CLI, so:
- `cihub` must be in PATH, OR
- User specifies Python path in config

```typescript
// src/lib/cihub.ts
async function findCihub(): Promise<string> {
 // Try PATH
 const inPath = await which("cihub").catch(() => null);
 if (inPath) return inPath;

 // Try Python module
 const python = process.env.PYTHON_PATH || "python";
 return `${python} -m cihub`;
}
```

---

## Part 11: Implementation Phases

### Phase 0: Prerequisites (CLEAN_CODE.md)
> Must complete before starting TypeScript CLI

- [ ] Fix 80 remaining print statements
- [ ] Ensure all commands return clean JSON on stdout
- [ ] Add JSON purity contract test

### Phase 1: Minimal Interactive CLI [3-4 days]

**Goal:** Basic Ink app that can run cihub commands

- [ ] Set up TypeScript + Ink project with tsup
- [ ] Create basic App component with header/input/output
- [ ] Implement Python CLI bridge (execa)
- [ ] Parse and execute raw `cihub <command>` input
- [ ] Display JSON output as formatted text

**Deliverable:** User can type `cihub discover` and see output.

### Phase 2: Slash Commands [2-3 days]

**Goal:** Parse `/command` syntax and route to handlers

- [ ] Create slash command parser
- [ ] Map slash commands to CLI commands
- [ ] Auto-append `--json` flag
- [ ] Implement `/help`, `/clear`, `/exit`
- [ ] Add command history (up/down arrows)
- [ ] Add tab completion for commands

**Deliverable:** User can type `/discover` and it works.

### Phase 3: Rich Output [3-4 days]

**Goal:** Render CommandResult JSON as beautiful UI

- [ ] Create Problems component with severity icons
- [ ] Create Suggestions component with bullets
- [ ] Create Table component for data display
- [ ] Add color coding (success=green, error=red)
- [ ] Add expandable/collapsible sections

**Deliverable:** Slash commands show rich formatted output.

### Phase 4: AI Integration [4-5 days]

**Goal:** Natural language queries

- [ ] Create `/ai` command handler
- [ ] Integrate Anthropic SDK or Claude CLI
- [ ] Define AI tool for running cihub
- [ ] Implement confirmation for write operations
- [ ] Add `/explain`, `/review`, `/plan` commands
- [ ] Stream AI responses to terminal

**Deliverable:** `/ai "what's failing?"` works.

### Phase 5: Polish & Distribution [2-3 days]

**Goal:** Production-ready npm package

- [ ] Add startup screen / welcome message
- [ ] Implement config file (~/.cihubrc)
- [ ] Add keyboard shortcuts
- [ ] Bundle into single file
- [ ] Publish to npm
- [ ] Create installation docs

---

## Part 12: Code Examples

### 12.1 Entry Point

```typescript
// src/index.tsx
#!/usr/bin/env node
import React from "react";
import { render } from "ink";
import { program } from "commander";
import { App } from "./app.js";

program
 .name("cihub")
 .description("Interactive CIHub CLI")
 .option("-d, --dir <path>", "Working directory", process.cwd())
 .action((options) => {
 render(<App cwd={options.dir} />);
 });

program.parse();
```

### 12.2 Main App Component

```tsx
// src/app.tsx
import React, { useState, useCallback } from "react";
import { Box, Text, useApp, useInput } from "ink";
import { TextInput } from "ink-text-input";
import Spinner from "ink-spinner";
import { Header } from "./components/Header.js";
import { Output } from "./components/Output.js";
import { parseSlashCommand, executeCommand } from "./lib/commands.js";
import type { CommandResult } from "./types/command-result.js";

interface AppProps {
 cwd: string;
}

export function App({ cwd }: AppProps) {
 const { exit } = useApp();
 const [input, setInput] = useState("");
 const [loading, setLoading] = useState(false);
 const [result, setResult] = useState<CommandResult | null>(null);
 const [history, setHistory] = useState<string[]>([]);

 const handleSubmit = useCallback(async (value: string) => {
 if (!value.trim()) return;

 // Add to history
 setHistory((h) => [...h, value]);
 setInput("");

 // Handle meta commands
 if (value === "/exit") {
 exit();
 return;
 }
 if (value === "/clear") {
 setResult(null);
 return;
 }

 // Execute command
 setLoading(true);
 try {
 const parsed = parseSlashCommand(value);
 const output = await executeCommand(parsed, cwd);
 setResult(output);
 } catch (error) {
 setResult({
 exit_code: 1,
 summary: `Error: ${error.message}`,
 problems: [{ severity: "error", message: error.message }],
 });
 } finally {
 setLoading(false);
 }
 }, [cwd, exit]);

 return (
 <Box flexDirection="column" padding={1}>
 <Header cwd={cwd} />

 {loading ? (
 <Box>
 <Spinner type="dots" />
 <Text> Running...</Text>
 </Box>
 ) : (
 result && <Output result={result} />
 )}

 <Box marginTop={1}>
 <Text color="green"> </Text>
 <TextInput
 value={input}
 onChange={setInput}
 onSubmit={handleSubmit}
 placeholder="Type /help or enter a command..."
 />
 </Box>
 </Box>
 );
}
```

### 12.3 Python CLI Bridge

```typescript
// src/lib/cihub.ts
import { execa, type ExecaReturnValue } from "execa";
import type { CommandResult } from "../types/command-result.js";

export async function runCihub(
 command: string,
 args: string[] = [],
 cwd: string
): Promise<CommandResult> {
 const fullArgs = [command, ...args, "--json"];

 try {
 const result = await execa("python", ["-m", "cihub", ...fullArgs], {
 cwd,
 reject: false, // Don't throw on non-zero exit
 });

 // Parse JSON from stdout
 const json = JSON.parse(result.stdout);
 return json as CommandResult;
 } catch (error) {
 // Handle JSON parse error or process error
 return {
 exit_code: 1,
 command,
 status: "error",
 duration_ms: 0,
 summary: `Failed to run cihub: ${error.message}`,
 problems: [{ severity: "error", message: error.message }],
 suggestions: [],
 files_generated: [],
 files_modified: [],
 artifacts: {},
 };
 }
}
```

### 12.4 Slash Command Parser

```typescript
// src/lib/parser.ts
export interface ParsedCommand {
 type: "slash" | "raw" | "ai";
 command: string;
 args: string[];
}

export function parseSlashCommand(input: string): ParsedCommand {
 const trimmed = input.trim();

 // Slash command: /discover --json
 if (trimmed.startsWith("/")) {
 const [cmd, ...rest] = trimmed.slice(1).split(/\s+/);

 // AI command
 if (cmd === "ai") {
 return {
 type: "ai",
 command: "ai",
 args: [rest.join(" ")], // Entire prompt
 };
 }

 return {
 type: "slash",
 command: cmd,
 args: rest,
 };
 }

 // Raw command: cihub discover
 if (trimmed.startsWith("cihub ")) {
 const [, cmd, ...rest] = trimmed.split(/\s+/);
 return {
 type: "raw",
 command: cmd,
 args: rest,
 };
 }

 // Default to AI prompt
 return {
 type: "ai",
 command: "ai",
 args: [trimmed],
 };
}
```

### Output Component

```tsx
// src/components/Output.tsx
import React from "react";
import { Box, Text } from "ink";
import type { CommandResult } from "../types/command-result.js";

const ICONS = {
 error: "[ ]",
 warning: "",
 info: "ℹ",
 success: "[x]",
 critical: "",
};

const COLORS = {
 error: "red",
 warning: "yellow",
 info: "blue",
 success: "green",
 critical: "magenta",
};

interface OutputProps {
 result: CommandResult;
}

export function Output({ result }: OutputProps) {
 return (
 <Box flexDirection="column" marginY={1}>
 {/* Summary */}
 <Text bold>{result.summary}</Text>

 {/* Problems */}
 {result.problems.length > 0 && (
 <Box flexDirection="column" marginTop={1}>
 {result.problems.map((p, i) => (
 <Text key={i} color={COLORS[p.severity] || "white"}>
 {ICONS[p.severity] || "•"} {p.message}
 </Text>
 ))}
 </Box>
 )}

 {/* Suggestions */}
 {result.suggestions.length > 0 && (
 <Box flexDirection="column" marginTop={1}>
 <Text bold>Suggestions:</Text>
 {result.suggestions.map((s, i) => (
 <Text key={i} color="cyan">• {s.message}</Text>
 ))}
 </Box>
 )}

 {/* Files */}
 {result.files_generated.length > 0 && (
 <Text color="green" marginTop={1}>
 Generated: {result.files_generated.join(", ")}
 </Text>
 )}
 </Box>
 );
}
```

---

## Part 13: Distribution

### npm Package

```bash
# Install globally
npm install -g @yourorg/cihub-cli

# Or run directly
npx @yourorg/cihub-cli
```

### Binary Entry Point

```javascript
// bin/cihub.js
#!/usr/bin/env node
import "../dist/index.js";
```

### Bundle Configuration

```typescript
// tsup.config.ts
import { defineConfig } from "tsup";

export default defineConfig({
 entry: ["src/index.tsx"],
 format: ["esm"],
 target: "node20",
 clean: true,
 minify: true,
 bundle: true,
 external: ["react", "ink"], // Don't bundle these
});
```

### Installation Requirements

- Node.js 20+ (or Bun)
- Python 3.10+ with `cihub` package installed
- Optional: Anthropic API key for AI features

---

## Appendix A: Full Slash Command Reference

### CIHub Commands (100+ total)

**Top-Level (29 commands):**
```
/detect, /preflight, /doctor, /scaffold, /smoke, /smoke-validate
/check, /verify, /ci, /run
/report (11 subcommands), /triage, /docs (3 subcommands), /adr (3 subcommands)
/config-outputs, /discover, /dispatch (2 subcommands)
/hub-ci (46 subcommands)
/new, /init, /update, /validate
/setup-secrets, /setup-nvd, /fix-pom, /fix-deps, /sync-templates
/config (6 subcommands)
```

**Report Subcommands (11):**
```
/report build, /report summary, /report outputs, /report aggregate
/report validate, /report dashboard, /report security-summary
/report smoke-summary, /report kyverno-summary, /report orchestrator-summary
```

**Config Subcommands (6):**
```
/config show, /config edit, /config set
/config enable, /config disable, /config apply-profile
```

**Hub-CI Subcommands (46):**
```
Validation: actionlint-install, actionlint, syntax, repo-check, source-check
 validate-configs, validate-profiles

Security: security-pip-audit, security-bandit, security-ruff, security-owasp
 docker-check, codeql-build, trivy-install, trivy-summary
 gitleaks-summary, license-check, zizmor-run, zizmor-check

Kyverno: kyverno-install, kyverno-validate, kyverno-test

Smoke: smoke-java-build, smoke-java-tests, smoke-java-coverage
 smoke-java-checkstyle, smoke-java-spotbugs
 smoke-python-install, smoke-python-tests, smoke-python-ruff
 smoke-python-black

Python: ruff, black, mutmut, bandit, pip-audit, pytest-summary

Release: release-parse, release-update, badges, badges-commit

Hub: summary, outputs, enforce, verify-matrix, quarantine
```

### Meta Commands (Interactive CLI Only)

```
/help - Show all commands
/help <cmd> - Show help for specific command
/clear - Clear screen
/exit - Exit CLI
/cd <path> - Change directory
/pwd - Show current directory
/history - Show command history
/reload - Reload configuration
/status - Show system status
```

### AI Commands

```
/ai <prompt> - Free-form AI query
/explain - Explain current state/last result
/explain <file> - Explain a specific file
/review - AI review of recent changes
/review <commit> - Review specific commit
/plan <task> - Create implementation plan
/fix - Suggest fix for last error
/fix <issue> - Suggest fix for specific issue
/suggest - AI suggestions for current state
/diagnose - Deep diagnosis of failures
```

---

## Appendix B: Comparison to Other Approaches

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **TypeScript + Ink** (this doc) | Same as Claude Code, rich UI | Cross-process overhead | Interactive CLI |
| **Python + Textual** | Same language as CLI | Different ecosystem | Python-only teams |
| **Rust + ratatui** | Maximum performance | High complexity | Performance-critical |
| **Tauri + xterm.js** | Desktop window with terminal | Not what Claude/Codex do | Desktop GUI app |

---

## Appendix C: Sources

- [How Claude Code is Built](https://newsletter.pragmaticengineer.com/p/how-claude-code-is-built) - Architecture deep-dive
- [Ink GitHub](https://github.com/vadimdemedes/ink) - React for CLIs
- [Codex CLI GitHub](https://github.com/openai/codex) - OpenAI's coding agent
- [Ink Tutorial - LogRocket](https://blog.logrocket.com/using-ink-ui-react-build-interactive-custom-clis/) - Step-by-step guide
- [Claude Code npm](https://www.npmjs.com/package/@anthropic-ai/claude-code) - Official package
- [How to Build CLIs Like Codex](https://levelup.gitconnected.com/how-to-use-ink-ui-to-build-beautiful-cli-tools-like-openais-codex-d793c752da5f) - Tutorial
- [Codex CLI Slash Commands](https://developers.openai.com/codex/cli/slash-commands/) - Official docs

---

## Part 14: CommandResult Schema

This section provides the **complete TypeScript schema** for CommandResult, ensuring TypeScript CLI and Python CLI outputs are perfectly aligned.

### 14.1 Python Source (cihub/types.py)

The authoritative source is the Python `CommandResult` dataclass:

```python
@dataclass
class CommandResult:
 """Structured command result for JSON output."""
 exit_code: int = 0
 summary: str = ""
 problems: list[dict[str, Any]] = field(default_factory=list)
 suggestions: list[dict[str, Any]] = field(default_factory=list)
 files_generated: list[str] = field(default_factory=list)
 files_modified: list[str] = field(default_factory=list)
 artifacts: dict[str, Any] = field(default_factory=dict)
 data: dict[str, Any] = field(default_factory=dict)
```

### 14.2 TypeScript Schema (Zod)

```typescript
// src/types/command-result.ts
import { z } from "zod";

/**
 * Problem severity levels
 */
export const SeveritySchema = z.enum([
 "critical",
 "error",
 "warning",
 "info",
 "success"
]);
export type Severity = z.infer<typeof SeveritySchema>;

/**
 * A problem/issue found by a command
 */
export const ProblemSchema = z.object({
 severity: SeveritySchema,
 message: z.string(),
 code: z.string().optional(), // e.g., "CIHUB-001", "CVE-2024-1234"
 file: z.string().optional(), // File path if applicable
 line: z.number().optional(), // Line number if applicable
 column: z.number().optional(), // Column if applicable
 hint: z.string().optional(), // Remediation hint
 source: z.string().optional(), // Tool that detected this (e.g., "ruff", "bandit")
});
export type Problem = z.infer<typeof ProblemSchema>;

/**
 * A suggestion for the user
 */
export const SuggestionSchema = z.object({
 message: z.string(),
 command: z.string().optional(), // Suggested command to run
 autofix: z.boolean().optional(), // Can be auto-fixed
 priority: z.number().optional(), // 1 = highest priority
});
export type Suggestion = z.infer<typeof SuggestionSchema>;

/**
 * Data rendering types (for HumanRenderer)
 */
export const DataSchema = z.object({
 items: z.array(z.string()).optional(), // Bullet list
 table: z.object({
 headers: z.array(z.string()).optional(),
 rows: z.array(z.record(z.unknown())).or(z.array(z.array(z.unknown()))),
 }).optional(),
 key_values: z.record(z.unknown()).optional(), // Key-value pairs
 raw_output: z.string().optional(), // Preformatted text
}).passthrough(); // Allow additional command-specific data

/**
 * The full JSON payload returned by `cihub <command> --json`
 */
export const CommandResultPayloadSchema = z.object({
 // Metadata (added by cli.py main())
 command: z.string(), // e.g., "triage", "hub-ci check-workflows"
 status: z.enum(["success", "failure", "error"]),
 exit_code: z.number().int().min(0).max(255),
 duration_ms: z.number().int().min(0),

 // Core result fields
 summary: z.string(),
 problems: z.array(ProblemSchema).default([]),
 suggestions: z.array(SuggestionSchema).default([]),

 // File operations
 files_generated: z.array(z.string()).default([]),
 files_modified: z.array(z.string()).default([]),

 // Artifacts (command-specific structured data)
 artifacts: z.record(z.unknown()).default({}),

 // Structured data for rendering
 data: DataSchema.optional(),
});
export type CommandResultPayload = z.infer<typeof CommandResultPayloadSchema>;

/**
 * Parse and validate JSON from Python CLI
 */
export function parseCommandResult(json: string): CommandResultPayload {
 const parsed = JSON.parse(json);
 return CommandResultPayloadSchema.parse(parsed);
}

/**
 * Check if result indicates success
 */
export function isSuccess(result: CommandResultPayload): boolean {
 return result.exit_code === 0 && result.status === "success";
}

/**
 * Get critical/error problems only
 */
export function getCriticalProblems(result: CommandResultPayload): Problem[] {
 return result.problems.filter(p =>
 p.severity === "critical" || p.severity === "error"
 );
}
```

### 14.3 Exit Code Semantics

| Exit Code | Constant | Meaning |
|-----------|----------|---------|
| 0 | `EXIT_SUCCESS` | Command completed successfully |
| 1 | `EXIT_FAILURE` | Command failed (expected error) |
| 2 | `EXIT_INTERNAL_ERROR` | Internal error (bug, unhandled exception) |

```typescript
// src/types/exit-codes.ts
export const EXIT_SUCCESS = 0;
export const EXIT_FAILURE = 1;
export const EXIT_INTERNAL_ERROR = 2;
```

### 14.4 Command-Specific Artifacts

Different commands populate the `artifacts` field with command-specific data:

| Command | Artifacts Schema |
|---------|-----------------|
| `discover` | `{ repos: RepoEntry[], count: number }` |
| `triage` | `{ bundle: TriageBundle, history?: FlakynessResult }` |
| `check` | `{ tools: ToolResult[], passed: boolean }` |
| `report build` | `{ report: Report, path: string }` |
| `hub-ci *` | Varies by subcommand |

```typescript
// Example: Triage-specific artifacts
export const TriageBundleSchema = z.object({
 overall_status: z.string(),
 tests_passed: z.number(),
 tests_failed: z.number(),
 tests_total: z.number(),
 coverage_pct: z.number().optional(),
 gate_failures: z.array(z.string()),
 warnings: z.array(z.object({
 type: z.string(),
 severity: z.string(),
 message: z.string(),
 })),
 tool_results: z.record(z.unknown()),
});
```

### 14.5 Contract Test Generator

Generate TypeScript schemas from Python at build time:

```typescript
// scripts/generate-schemas.ts
import { execSync } from "child_process";
import { writeFileSync } from "fs";

// Run Python introspection to get actual types
const pythonScript = `
import json
from cihub.types import CommandResult
from dataclasses import fields
print(json.dumps([{"name": f.name, "type": str(f.type)} for f in fields(CommandResult)]))
`;

const output = execSync(`python -c '${pythonScript}'`).toString();
const fields = JSON.parse(output);

// Generate Zod schema from Python fields
// ... schema generation logic
```

---

## Part 15: Testing Strategy

This section defines the **complete testing strategy** for the TypeScript CLI, ensuring reliability and maintainability.

### 15.1 Test Pyramid

```
 ┌─────────┐
 │ E2E │ 2-3 tests (full flows)
 │ Tests │
 ┌┴─────────┴┐
 │Integration│ 10-20 tests (CLI bridge)
 │ Tests │
 ┌┴───────────┴┐
 │ Component │ 30-50 tests (React/Ink)
 │ Tests │
 ┌┴─────────────┴┐
 │ Unit │ 100+ tests (logic, parsing)
 │ Tests │
 └───────────────┘
```

### 15.2 Contract Tests (Critical)

**Contract tests ensure TypeScript and Python stay in sync.**

```typescript
// test/contracts/json-purity.test.ts
import { describe, test, expect } from "vitest";
import { execa } from "execa";
import { CommandResultPayloadSchema } from "../src/types/command-result";

/**
 * All commands that support --json flag
 */
const JSON_COMMANDS = [
 ["detect"],
 ["preflight"],
 ["discover"],
 ["triage"],
 ["check"],
 ["verify"],
 ["ci"],
 ["report", "build"],
 ["report", "summary"],
 ["config", "show"],
 ["hub-ci", "check-workflows"],
 // ... all 100+ commands
] as const;

describe("JSON Output Contract", () => {
 test.each(JSON_COMMANDS)(
 "cihub %s --json returns valid JSON",
 async (...args) => {
 const { stdout, exitCode } = await execa(
 "python", ["-m", "cihub", ...args, "--json"],
 { reject: false }
 );

 // Must parse as JSON
 expect(() => JSON.parse(stdout)).not.toThrow();

 // Must match schema
 const parsed = JSON.parse(stdout);
 expect(() => CommandResultPayloadSchema.parse(parsed)).not.toThrow();

 // exit_code in JSON must match process exit code
 expect(parsed.exit_code).toBe(exitCode);
 },
 { timeout: 30000 }
 );
});
```

```typescript
// test/contracts/schema-sync.test.ts
import { describe, test, expect } from "vitest";
import { execa } from "execa";

describe("Schema Synchronization", () => {
 test("Python CommandResult fields match TypeScript schema", async () => {
 // Extract Python fields via introspection
 const script = `
import json
from dataclasses import fields
from cihub.types import CommandResult
print(json.dumps({f.name: str(f.type) for f in fields(CommandResult)}))
 `;
 const { stdout } = await execa("python", ["-c", script]);
 const pythonFields = JSON.parse(stdout);

 // Expected fields from TypeScript
 const expectedFields = [
 "exit_code", "summary", "problems", "suggestions",
 "files_generated", "files_modified", "artifacts", "data"
 ];

 for (const field of expectedFields) {
 expect(pythonFields).toHaveProperty(field);
 }
 });
});
```

### 15.3 Component Tests (Ink/React)

```typescript
// test/components/Output.test.tsx
import React from "react";
import { render } from "ink-testing-library";
import { describe, test, expect } from "vitest";
import { Output } from "../src/components/Output";

describe("Output Component", () => {
 test("renders summary", () => {
 const result = {
 exit_code: 0,
 summary: "Found 3 repos",
 problems: [],
 suggestions: [],
 files_generated: [],
 files_modified: [],
 artifacts: {},
 command: "discover",
 status: "success" as const,
 duration_ms: 100,
 };

 const { lastFrame } = render(<Output result={result} />);
 expect(lastFrame()).toContain("Found 3 repos");
 });

 test("renders problems with severity icons", () => {
 const result = {
 exit_code: 1,
 summary: "Check failed",
 problems: [
 { severity: "error" as const, message: "Ruff found 5 errors" },
 { severity: "warning" as const, message: "Coverage below 80%" },
 ],
 suggestions: [],
 files_generated: [],
 files_modified: [],
 artifacts: {},
 command: "check",
 status: "failure" as const,
 duration_ms: 500,
 };

 const { lastFrame } = render(<Output result={result} />);
 expect(lastFrame()).toContain("[ ]"); // Error icon
 expect(lastFrame()).toContain(""); // Warning icon
 expect(lastFrame()).toContain("Ruff found 5 errors");
 });

 test("renders suggestions", () => {
 const result = {
 exit_code: 1,
 summary: "Issues found",
 problems: [],
 suggestions: [
 { message: "Run /check --fix to auto-fix" },
 ],
 files_generated: [],
 files_modified: [],
 artifacts: {},
 command: "check",
 status: "failure" as const,
 duration_ms: 200,
 };

 const { lastFrame } = render(<Output result={result} />);
 expect(lastFrame()).toContain("Suggestions:");
 expect(lastFrame()).toContain("/check --fix");
 });
});
```

### 15.4 Integration Tests (CLI Bridge)

```typescript
// test/integration/cihub-bridge.test.ts
import { describe, test, expect, beforeAll } from "vitest";
import { runCihub } from "../src/lib/cihub";
import { tmpdir } from "os";
import { mkdtemp, writeFile, rm } from "fs/promises";
import { join } from "path";

describe("CIHub Bridge", () => {
 let testDir: string;

 beforeAll(async () => {
 // Create temp directory with minimal Python project
 testDir = await mkdtemp(join(tmpdir(), "cihub-test-"));
 await writeFile(
 join(testDir, "pyproject.toml"),
 '[project]\nname = "test"\nversion = "0.1.0"'
 );
 });

 afterAll(async () => {
 await rm(testDir, { recursive: true, force: true });
 });

 test("discover returns valid CommandResult", async () => {
 const result = await runCihub("discover", [], testDir);

 expect(result.command).toBe("discover");
 expect(typeof result.exit_code).toBe("number");
 expect(typeof result.duration_ms).toBe("number");
 expect(result.duration_ms).toBeGreaterThan(0);
 });

 test("handles missing command gracefully", async () => {
 const result = await runCihub("nonexistent", [], testDir);

 expect(result.exit_code).not.toBe(0);
 expect(result.problems.length).toBeGreaterThan(0);
 });

 test("passes arguments correctly", async () => {
 const result = await runCihub("check", ["--verbose"], testDir);

 // Command should receive the flag
 expect(result.command).toBe("check");
 });
});
```

### 15.5 E2E Tests (Full Flows)

```typescript
// test/e2e/full-workflow.test.ts
import { describe, test, expect } from "vitest";
import { render } from "ink-testing-library";
import { App } from "../src/app";

describe("E2E Workflows", () => {
 test("complete triage flow", async () => {
 const { stdin, lastFrame, waitForFrame } = render(
 <App cwd="/tmp/test-project" />
 );

 // Type /triage command
 stdin.write("/triage\n");

 // Wait for loading to complete
 await waitForFrame((frame) => !frame.includes("Running..."));

 // Should show triage output
 const output = lastFrame();
 expect(output).toContain("triage");
 });

 test("AI query flow", async () => {
 const { stdin, lastFrame, waitForFrame } = render(
 <App cwd="/tmp/test-project" />
 );

 // Type AI query
 stdin.write("/ai what is failing?\n");

 // Wait for AI response
 await waitForFrame((frame) => !frame.includes("Running..."), {
 timeout: 30000
 });

 // Should show AI response
 expect(lastFrame()).toBeTruthy();
 });
});
```

### 15.6 Test Configuration

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
 test: {
 include: ["test/**/*.test.{ts,tsx}"],
 globals: true,
 environment: "node",
 coverage: {
 provider: "v8",
 reporter: ["text", "json", "html"],
 thresholds: {
 lines: 80,
 functions: 80,
 branches: 70,
 statements: 80,
 },
 },
 testTimeout: 30000, // 30s for CLI tests
 hookTimeout: 10000,
 },
});
```

### 15.7 CI Integration

```yaml
# .github/workflows/test.yml
name: Test TypeScript CLI
on: [push, pull_request]

jobs:
 test:
 runs-on: ubuntu-latest
 steps:
 - uses: actions/checkout@v4

 - uses: actions/setup-node@v4
 with:
 node-version: '20'

 - uses: actions/setup-python@v5
 with:
 python-version: '3.12'

 - name: Install Python CLI
 run: pip install -e .

 - name: Install TypeScript dependencies
 run: pnpm install
 working-directory: cihub-cli

 - name: Run tests
 run: pnpm test
 working-directory: cihub-cli

 - name: Contract tests
 run: pnpm test:contracts
 working-directory: cihub-cli
```

---

## Part 16: Error Handling Patterns

This section defines **concrete error handling patterns** for all failure modes.

### 16.1 Error Categories

| Category | Cause | Handling |
|----------|-------|----------|
| **Network** | API timeout, DNS failure | Retry with backoff |
| **Process** | CLI crash, timeout | Return error CommandResult |
| **Parse** | Invalid JSON, schema mismatch | Fallback to raw output |
| **User** | Invalid input, missing file | Show helpful message |
| **System** | Out of memory, disk full | Exit gracefully |

### 16.2 CLI Bridge Error Handling

```typescript
// src/lib/cihub.ts
import { execa, ExecaError } from "execa";
import { CommandResultPayloadSchema, type CommandResultPayload } from "../types/command-result";

/**
 * Configuration for CLI execution
 */
interface CihubOptions {
 timeout?: number; // Default: 120000 (2 minutes)
 maxRetries?: number; // Default: 0 (no retry)
 retryDelay?: number; // Default: 1000ms
}

const DEFAULT_OPTIONS: Required<CihubOptions> = {
 timeout: 120000,
 maxRetries: 0,
 retryDelay: 1000,
};

/**
 * Run cihub command with comprehensive error handling
 */
export async function runCihub(
 command: string,
 args: string[] = [],
 cwd: string,
 options: CihubOptions = {}
): Promise<CommandResultPayload> {
 const opts = { ...DEFAULT_OPTIONS, ...options };
 const fullArgs = ["-m", "cihub", command, ...args, "--json"];

 let lastError: Error | null = null;

 for (let attempt = 0; attempt <= opts.maxRetries; attempt++) {
 try {
 const result = await execa("python", fullArgs, {
 cwd,
 timeout: opts.timeout,
 reject: false, // Don't throw on non-zero exit
 stripFinalNewline: true,
 });

 // Try to parse JSON from stdout
 return parseOutput(result.stdout, result.exitCode, command);

 } catch (error) {
 lastError = error as Error;

 if (isTimeoutError(error)) {
 // Timeout - maybe retry
 if (attempt < opts.maxRetries) {
 await sleep(opts.retryDelay);
 continue;
 }
 return createErrorResult(command, `Command timed out after ${opts.timeout}ms`);
 }

 if (isProcessError(error)) {
 // Process crashed
 return createErrorResult(command, `Process failed: ${(error as ExecaError).message}`);
 }

 // Unknown error
 throw error;
 }
 }

 return createErrorResult(command, lastError?.message || "Unknown error");
}

/**
 * Parse stdout, with fallback for invalid JSON
 */
function parseOutput(
 stdout: string,
 exitCode: number,
 command: string
): CommandResultPayload {
 // Empty output
 if (!stdout.trim()) {
 return createErrorResult(command, "Command produced no output", exitCode);
 }

 // Try JSON parse
 let parsed: unknown;
 try {
 parsed = JSON.parse(stdout);
 } catch (e) {
 // JSON parse failed - output may contain non-JSON content
 return {
 command,
 status: exitCode === 0 ? "success" : "failure",
 exit_code: exitCode,
 duration_ms: 0,
 summary: "Command output was not valid JSON",
 problems: [{
 severity: "warning",
 message: "Output contained non-JSON content",
 }],
 suggestions: [],
 files_generated: [],
 files_modified: [],
 artifacts: {},
 data: { raw_output: stdout },
 };
 }

 // Validate against schema
 const validation = CommandResultPayloadSchema.safeParse(parsed);
 if (!validation.success) {
 return {
 command,
 status: exitCode === 0 ? "success" : "failure",
 exit_code: exitCode,
 duration_ms: 0,
 summary: "Command output did not match expected schema",
 problems: [{
 severity: "warning",
 message: `Schema validation: ${validation.error.message}`,
 }],
 suggestions: [],
 files_generated: [],
 files_modified: [],
 artifacts: {},
 data: parsed as Record<string, unknown>,
 };
 }

 return validation.data;
}

/**
 * Create an error CommandResult
 */
function createErrorResult(
 command: string,
 message: string,
 exitCode: number = 1
): CommandResultPayload {
 return {
 command,
 status: "error",
 exit_code: exitCode,
 duration_ms: 0,
 summary: message,
 problems: [{
 severity: "error",
 message,
 code: "CIHUB-CLI-ERROR",
 }],
 suggestions: [],
 files_generated: [],
 files_modified: [],
 artifacts: {},
 };
}

function isTimeoutError(error: unknown): boolean {
 return error instanceof Error && error.name === "TimeoutError";
}

function isProcessError(error: unknown): boolean {
 return error instanceof Error && "exitCode" in error;
}

function sleep(ms: number): Promise<void> {
 return new Promise(resolve => setTimeout(resolve, ms));
}
```

### 16.3 React Error Boundaries

```typescript
// src/components/ErrorBoundary.tsx
import React, { Component, type ReactNode } from "react";
import { Box, Text } from "ink";

interface Props {
 children: ReactNode;
 fallback?: ReactNode;
}

interface State {
 hasError: boolean;
 error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
 constructor(props: Props) {
 super(props);
 this.state = { hasError: false };
 }

 static getDerivedStateFromError(error: Error): State {
 return { hasError: true, error };
 }

 componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
 console.error("ErrorBoundary caught:", error, errorInfo);
 }

 render() {
 if (this.state.hasError) {
 if (this.props.fallback) {
 return this.props.fallback;
 }

 return (
 <Box flexDirection="column" padding={1}>
 <Text color="red" bold>Something went wrong</Text>
 <Text color="gray">{this.state.error?.message}</Text>
 <Text color="cyan">Press Ctrl+C to exit, or try another command.</Text>
 </Box>
 );
 }

 return this.props.children;
 }
}
```

### 16.4 Command-Specific Timeouts

| Command | Default Timeout | Rationale |
|---------|-----------------|-----------|
| `detect` | 5s | Fast local scan |
| `discover` | 30s | GitHub API calls |
| `triage` | 120s | Artifact download + analysis |
| `triage --run` | 300s | Remote artifact fetch |
| `check` | 60s | Tool execution |
| `check --all` | 600s | All tools including mutation |
| `hub-ci *` | 60s | Most hub-ci commands |
| `report dashboard` | 300s | Aggregation |

```typescript
// src/lib/timeouts.ts
export const COMMAND_TIMEOUTS: Record<string, number> = {
 "detect": 5000,
 "discover": 30000,
 "triage": 120000,
 "check": 60000,
 "verify": 60000,
 "report dashboard": 300000,
 "report aggregate": 300000,
};

export function getTimeout(command: string): number {
 return COMMAND_TIMEOUTS[command] ?? 120000; // Default 2 minutes
}
```

### 16.5 AI Error Handling

```typescript
// src/lib/ai-client.ts
import Anthropic from "@anthropic-ai/sdk";

interface AIOptions {
 timeout?: number; // API timeout
 maxRetries?: number; // Retry on rate limit
}

export class AIError extends Error {
 constructor(
 message: string,
 public code: string,
 public retryable: boolean
 ) {
 super(message);
 this.name = "AIError";
 }
}

export async function runAI(
 prompt: string,
 context: AIContext,
 options: AIOptions = {}
): Promise<string> {
 const client = new Anthropic({
 timeout: options.timeout ?? 60000,
 maxRetries: options.maxRetries ?? 2,
 });

 try {
 const response = await client.messages.create({
 model: "claude-sonnet-4-20250514",
 max_tokens: 4096,
 messages: [{ role: "user", content: prompt }],
 });

 const text = response.content.find(c => c.type === "text");
 return text?.text ?? "";

 } catch (error) {
 if (error instanceof Anthropic.APIError) {
 // Rate limit
 if (error.status === 429) {
 throw new AIError(
 "Rate limit exceeded. Please wait a moment.",
 "RATE_LIMIT",
 true
 );
 }

 // Auth error
 if (error.status === 401) {
 throw new AIError(
 "Invalid API key. Run: export ANTHROPIC_API_KEY=your-key",
 "AUTH_ERROR",
 false
 );
 }

 // Server error
 if (error.status >= 500) {
 throw new AIError(
 "AI service temporarily unavailable",
 "SERVER_ERROR",
 true
 );
 }
 }

 throw new AIError(
 `AI error: ${(error as Error).message}`,
 "UNKNOWN",
 false
 );
 }
}
```

### 16.6 User-Facing Error Messages

```typescript
// src/lib/errors.ts
export const ERROR_MESSAGES: Record<string, string> = {
 // Python CLI errors
 "ENOENT": "Python not found. Install Python 3.10+ and ensure it's in PATH.",
 "CIHUB_NOT_FOUND": "cihub package not found. Run: pip install cihub",
 "TIMEOUT": "Command timed out. Try running with --verbose for details.",

 // JSON errors
 "JSON_PARSE": "Invalid JSON output. The Python CLI may have printed non-JSON content.",
 "SCHEMA_MISMATCH": "Output schema mismatch. TypeScript CLI may need updating.",

 // AI errors
 "RATE_LIMIT": "AI rate limit reached. Wait a moment and try again.",
 "AUTH_ERROR": "Missing API key. Set ANTHROPIC_API_KEY environment variable.",
 "NO_AI": "AI features require an API key. Run without /ai commands, or configure API key.",

 // File errors
 "FILE_NOT_FOUND": "File not found. Check the path and try again.",
 "PERMISSION_DENIED": "Permission denied. Check file permissions.",
};

export function getUserMessage(code: string): string {
 return ERROR_MESSAGES[code] ?? "An unexpected error occurred.";
}
```

---

## Part 17: Configuration File Format

This section defines the **~/.cihubrc** configuration file format for user preferences.

### 17.1 Configuration Locations

| Location | Priority | Purpose |
|----------|----------|---------|
| `~/.cihubrc` | 1 (highest) | User global config |
| `~/.config/cihub/config.yaml` | 2 | XDG-compliant alternative |
| `.cihubrc` (cwd) | 3 | Project-specific override |
| Environment variables | 4 | Runtime override |

### 17.2 Configuration Schema

```yaml
# ~/.cihubrc
# CIHub Interactive CLI Configuration

# Python CLI settings
cli:
 # Path to Python executable (default: auto-detect)
 python_path: "/usr/bin/python3"

 # Default timeout for commands (ms)
 default_timeout: 120000

 # Enable verbose output by default
 verbose: false

# AI settings
ai:
 # Enable AI features (default: true if API key present)
 enabled: true

 # AI provider: "anthropic" | "openai" | "local"
 provider: "anthropic"

 # Model to use
 model: "claude-sonnet-4-20250514"

 # Max tokens for AI responses
 max_tokens: 4096

 # Temperature (0.0 - 1.0)
 temperature: 0.3

 # API key (prefer env var ANTHROPIC_API_KEY)
 # api_key: "sk-..." # NOT RECOMMENDED - use env var

# UI settings
ui:
 # Color theme: "auto" | "dark" | "light" | "none"
 theme: "auto"

 # Show command duration
 show_duration: true

 # Enable unicode icons (disable for basic terminals)
 unicode_icons: true

 # Max width for output (0 = auto)
 max_width: 0

 # Spinner style: "dots" | "line" | "simple"
 spinner: "dots"

# Command aliases
aliases:
 t: "triage"
 d: "discover"
 c: "check"
 h: "hub-ci"

# Default arguments for commands
defaults:
 triage:
 - "--detect-flaky"
 check:
 - "--verbose"
 discover:
 - "--json"

# Keyboard shortcuts (Ink key names)
shortcuts:
 ctrl+t: "/triage"
 ctrl+d: "/discover"
 ctrl+r: "/reload"
```

### 17.3 TypeScript Configuration Loader

```typescript
// src/lib/config.ts
import { z } from "zod";
import { readFile } from "fs/promises";
import { homedir } from "os";
import { join } from "path";
import { parse as parseYaml } from "yaml";

/**
 * Configuration schema
 */
const ConfigSchema = z.object({
 cli: z.object({
 python_path: z.string().optional(),
 default_timeout: z.number().default(120000),
 verbose: z.boolean().default(false),
 }).default({}),

 ai: z.object({
 enabled: z.boolean().default(true),
 provider: z.enum(["anthropic", "openai", "local"]).default("anthropic"),
 model: z.string().default("claude-sonnet-4-20250514"),
 max_tokens: z.number().default(4096),
 temperature: z.number().min(0).max(1).default(0.3),
 api_key: z.string().optional(),
 }).default({}),

 ui: z.object({
 theme: z.enum(["auto", "dark", "light", "none"]).default("auto"),
 show_duration: z.boolean().default(true),
 unicode_icons: z.boolean().default(true),
 max_width: z.number().default(0),
 spinner: z.enum(["dots", "line", "simple"]).default("dots"),
 }).default({}),

 aliases: z.record(z.string()).default({}),
 defaults: z.record(z.array(z.string())).default({}),
 shortcuts: z.record(z.string()).default({}),
}).default({});

export type Config = z.infer<typeof ConfigSchema>;

/**
 * Load configuration from all sources
 */
export async function loadConfig(cwd: string): Promise<Config> {
 const sources = [
 join(homedir(), ".cihubrc"),
 join(homedir(), ".config", "cihub", "config.yaml"),
 join(cwd, ".cihubrc"),
 ];

 let merged: Partial<Config> = {};

 for (const source of sources) {
 try {
 const content = await readFile(source, "utf-8");
 const parsed = parseYaml(content);
 merged = deepMerge(merged, parsed);
 } catch {
 // File doesn't exist or is invalid - skip
 }
 }

 // Apply environment variable overrides
 if (process.env.ANTHROPIC_API_KEY) {
 merged.ai = merged.ai ?? {};
 merged.ai.api_key = process.env.ANTHROPIC_API_KEY;
 }

 if (process.env.CIHUB_PYTHON_PATH) {
 merged.cli = merged.cli ?? {};
 merged.cli.python_path = process.env.CIHUB_PYTHON_PATH;
 }

 return ConfigSchema.parse(merged);
}

/**
 * Deep merge objects
 */
function deepMerge<T extends object>(target: T, source: Partial<T>): T {
 const result = { ...target };

 for (const key in source) {
 const sourceValue = source[key];
 const targetValue = target[key];

 if (isObject(sourceValue) && isObject(targetValue)) {
 (result as Record<string, unknown>)[key] = deepMerge(
 targetValue as object,
 sourceValue as object
 );
 } else if (sourceValue !== undefined) {
 (result as Record<string, unknown>)[key] = sourceValue;
 }
 }

 return result;
}

function isObject(value: unknown): value is object {
 return typeof value === "object" && value !== null && !Array.isArray(value);
}
```

### 17.4 Configuration Context

```typescript
// src/context/ConfigContext.tsx
import React, { createContext, useContext, useState, useEffect } from "react";
import { loadConfig, type Config } from "../lib/config";

const ConfigContext = createContext<Config | null>(null);

interface ConfigProviderProps {
 cwd: string;
 children: React.ReactNode;
}

export function ConfigProvider({ cwd, children }: ConfigProviderProps) {
 const [config, setConfig] = useState<Config | null>(null);

 useEffect(() => {
 loadConfig(cwd).then(setConfig);
 }, [cwd]);

 if (!config) {
 return null; // Or loading spinner
 }

 return (
 <ConfigContext.Provider value={config}>
 {children}
 </ConfigContext.Provider>
 );
}

export function useConfig(): Config {
 const config = useContext(ConfigContext);
 if (!config) {
 throw new Error("useConfig must be used within ConfigProvider");
 }
 return config;
}
```

### 17.5 Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) | `sk-...` |
| `CIHUB_PYTHON_PATH` | Path to Python executable | `/usr/local/bin/python3.12` |
| `CIHUB_DEBUG` | Enable debug logging | `1` |
| `CIHUB_NO_COLOR` | Disable colors | `1` |
| `CIHUB_CONFIG` | Custom config file path | `/path/to/config.yaml` |

### 17.6 First-Run Setup

On first run without config, show setup wizard:

```typescript
// src/components/FirstRunSetup.tsx
import React, { useState } from "react";
import { Box, Text } from "ink";
import SelectInput from "ink-select-input";
import TextInput from "ink-text-input";
import { writeFile } from "fs/promises";
import { homedir } from "os";
import { join } from "path";
import { stringify as stringifyYaml } from "yaml";

export function FirstRunSetup({ onComplete }: { onComplete: () => void }) {
 const [step, setStep] = useState(0);
 const [config, setConfig] = useState<Partial<Config>>({});

 const steps = [
 {
 question: "Enable AI features?",
 type: "confirm",
 key: "ai.enabled",
 default: true,
 },
 {
 question: "AI provider:",
 type: "select",
 key: "ai.provider",
 choices: ["anthropic", "openai", "local"],
 default: "anthropic",
 },
 // ... more steps
 ];

 const handleComplete = async () => {
 const configPath = join(homedir(), ".cihubrc");
 await writeFile(configPath, stringifyYaml(config));
 onComplete();
 };

 // ... render steps
}
```

---

## Part 18: Accessibility

**Critical:** Accessibility is not optional. CLI tools must work for users with screen readers, color blindness, motion sensitivity, and in constrained environments (CI pipelines, dumb terminals).

### 18.1 Environment Variable Support

```typescript
// src/lib/accessibility.ts

/**
 * Detect accessibility preferences from environment
 */
export function getAccessibilitySettings(): AccessibilitySettings {
 return {
 // NO_COLOR: Disable all colors (https://no-color.org/)
 noColor: Boolean(process.env.NO_COLOR),

 // TERM=dumb: Very basic terminal, disable all formatting
 dumbTerminal: process.env.TERM === "dumb",

 // CI: Running in CI pipeline, assume non-interactive
 isCI: Boolean(process.env.CI),

 // Force colors even if not TTY (for tools that support it)
 forceColor: Boolean(process.env.FORCE_COLOR),

 // Ink's screen reader mode
 screenReader: Boolean(process.env.INK_SCREEN_READER),

 // Reduce motion for users with motion sensitivity
 reduceMotion: Boolean(process.env.CIHUB_NO_ANIMATION),
 };
}

interface AccessibilitySettings {
 noColor: boolean;
 dumbTerminal: boolean;
 isCI: boolean;
 forceColor: boolean;
 screenReader: boolean;
 reduceMotion: boolean;
}

/**
 * Should we use colors?
 */
export function shouldUseColor(settings: AccessibilitySettings): boolean {
 if (settings.noColor) return false;
 if (settings.dumbTerminal) return false;
 if (settings.forceColor) return true;
 return process.stdout.isTTY ?? false;
}

/**
 * Should we use animations (spinners, progress bars)?
 */
export function shouldAnimate(settings: AccessibilitySettings): boolean {
 if (settings.reduceMotion) return false;
 if (settings.dumbTerminal) return false;
 if (settings.isCI) return false;
 if (settings.screenReader) return false;
 return process.stdout.isTTY ?? false;
}

/**
 * Should we use unicode characters?
 */
export function shouldUseUnicode(settings: AccessibilitySettings): boolean {
 if (settings.dumbTerminal) return false;
 // Check locale for unicode support
 const lang = process.env.LANG || "";
 return lang.includes("UTF-8") || lang.includes("utf8");
}
```

### 18.2 CLI Flags for Accessibility

```typescript
// In CLI argument parser
const accessibilityFlags = {
 "--no-color": "Disable all colors",
 "--no-animation": "Disable spinners and animations",
 "--plain": "Plain text output (no colors, no unicode, no formatting)",
 "--static": "Static output mode (no dynamic updates)",
};

// Usage
function parseArgs(argv: string[]): CliOptions {
 return {
 // ... other options
 noColor: argv.includes("--no-color") || argv.includes("--plain"),
 noAnimation: argv.includes("--no-animation") || argv.includes("--plain"),
 static: argv.includes("--static") || argv.includes("--plain"),
 };
}
```

### 18.3 Icon Fallbacks

```typescript
// src/lib/icons.ts

/**
 * Icons with ASCII fallbacks
 */
export function getIcons(useUnicode: boolean) {
 if (useUnicode) {
 return {
 success: "[x]",
 error: "[ ]",
 warning: "",
 info: "ℹ",
 spinner: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
 bullet: "•",
 arrow: "→",
 };
 }

 // ASCII fallbacks
 return {
 success: "[OK]",
 error: "[ERR]",
 warning: "[WARN]",
 info: "[INFO]",
 spinner: ["-", "\\", "|", "/"],
 bullet: "*",
 arrow: "->",
 };
}
```

### 18.4 TTY vs Non-TTY Detection

```typescript
// src/lib/output.ts

/**
 * Detect if running interactively or piped
 */
export function isInteractive(): boolean {
 return Boolean(
 process.stdin.isTTY &&
 process.stdout.isTTY &&
 !process.env.CI
 );
}

/**
 * Render output appropriately for context
 */
export function renderOutput(result: CommandResult): string {
 if (isInteractive()) {
 // Full interactive output with colors/formatting
 return renderInteractive(result);
 } else {
 // Plain output for piping/CI
 return renderPlain(result);
 }
}
```

### 18.5 Screen Reader Considerations

```typescript
// src/components/AccessibleOutput.tsx
import React from "react";
import { Box, Text, Static } from "ink";

interface Props {
 result: CommandResult;
 screenReaderMode: boolean;
}

export function AccessibleOutput({ result, screenReaderMode }: Props) {
 if (screenReaderMode) {
 // Use Static to prevent screen reader from reading dynamic updates
 return (
 <Static items={[result]}>
 {(item) => (
 <Box key="result" flexDirection="column">
 <Text>Command: {item.command}</Text>
 <Text>Status: {item.status}</Text>
 <Text>Summary: {item.summary}</Text>
 {item.problems.map((p, i) => (
 <Text key={i}>
 {p.severity.toUpperCase()}: {p.message}
 </Text>
 ))}
 </Box>
 )}
 </Static>
 );
 }

 // Normal interactive output
 return <Output result={result} />;
}
```

### 18.6 Testing Accessibility

```typescript
// test/accessibility/no-color.test.ts
import { describe, test, expect, beforeEach, afterEach } from "vitest";

describe("NO_COLOR support", () => {
 const originalEnv = process.env;

 beforeEach(() => {
 process.env = { ...originalEnv };
 });

 afterEach(() => {
 process.env = originalEnv;
 });

 test("disables colors when NO_COLOR is set", () => {
 process.env.NO_COLOR = "1";
 const settings = getAccessibilitySettings();
 expect(shouldUseColor(settings)).toBe(false);
 });

 test("disables colors when TERM=dumb", () => {
 process.env.TERM = "dumb";
 const settings = getAccessibilitySettings();
 expect(shouldUseColor(settings)).toBe(false);
 });
});

// test/accessibility/screen-reader.test.ts
describe("Screen reader mode", () => {
 test("uses Static component to prevent re-reads", () => {
 process.env.INK_SCREEN_READER = "true";
 // Verify Static is used, no dynamic updates
 });

 test("provides text alternatives to icons", () => {
 // Verify [OK] instead of [x] when unicode disabled
 });
});
```

---

## Part 19: Process Management

**Critical:** The CLI must handle process lifecycle correctly - graceful shutdown, signal handling, and subprocess cleanup.

### 19.1 Signal Handling

```typescript
// src/lib/signals.ts
import { ChildProcess } from "child_process";

// Track active child processes for cleanup
const activeChildren: Set<ChildProcess> = new Set();

/**
 * Register a child process for cleanup
 */
export function registerChild(child: ChildProcess): void {
 activeChildren.add(child);
 child.on("exit", () => activeChildren.delete(child));
}

/**
 * Setup signal handlers for graceful shutdown
 */
export function setupSignalHandlers(onShutdown: () => Promise<void>): void {
 let isShuttingDown = false;

 async function handleSignal(signal: string): Promise<void> {
 if (isShuttingDown) {
 // Force exit on second signal
 console.error("\nForce quitting...");
 process.exit(1);
 }

 isShuttingDown = true;
 console.error(`\nReceived ${signal}, shutting down gracefully...`);

 // Kill child processes
 for (const child of activeChildren) {
 child.kill(signal as NodeJS.Signals);
 }

 // Give processes time to cleanup
 const timeout = setTimeout(() => {
 console.error("Shutdown timeout, forcing exit");
 process.exit(1);
 }, 5000);

 try {
 await onShutdown();
 clearTimeout(timeout);
 process.exit(0);
 } catch (error) {
 clearTimeout(timeout);
 console.error("Error during shutdown:", error);
 process.exit(1);
 }
 }

 process.on("SIGINT", () => handleSignal("SIGINT"));
 process.on("SIGTERM", () => handleSignal("SIGTERM"));

 // Handle uncaught errors
 process.on("uncaughtException", (error) => {
 console.error("Uncaught exception:", error);
 handleSignal("uncaughtException");
 });

 process.on("unhandledRejection", (reason) => {
 console.error("Unhandled rejection:", reason);
 handleSignal("unhandledRejection");
 });
}
```

### 19.2 Graceful Shutdown in Ink

```typescript
// src/app.tsx
import React, { useEffect } from "react";
import { useApp } from "ink";
import { setupSignalHandlers } from "./lib/signals";

export function App() {
 const { exit } = useApp();

 useEffect(() => {
 setupSignalHandlers(async () => {
 // Cleanup logic
 await saveCommandHistory();
 await flushLogs();
 exit();
 });
 }, [exit]);

 // ... rest of app
}
```

### 19.3 Subprocess Management

```typescript
// src/lib/cihub.ts (updated)
import { execa, ExecaChildProcess } from "execa";
import { registerChild } from "./signals";

/**
 * Run cihub command with proper process management
 */
export async function runCihub(
 command: string,
 args: string[],
 cwd: string,
 options: CihubOptions = {}
): Promise<CommandResultPayload> {
 const subprocess = execa("python", ["-m", "cihub", command, ...args, "--json"], {
 cwd,
 timeout: options.timeout ?? 120000,
 reject: false,
 // Don't buffer - stream for large outputs
 buffer: false,
 });

 // Register for cleanup on shutdown
 registerChild(subprocess as unknown as ChildProcess);

 // Collect output
 let stdout = "";
 let stderr = "";

 subprocess.stdout?.on("data", (data) => {
 stdout += data.toString();
 });

 subprocess.stderr?.on("data", (data) => {
 stderr += data.toString();
 });

 const result = await subprocess;

 return parseOutput(stdout, result.exitCode ?? 1, command);
}
```

### 19.4 Version Compatibility Check

```typescript
// src/lib/version.ts
import { execa } from "execa";

interface VersionInfo {
 typescript: string;
 python: string;
 compatible: boolean;
 message?: string;
}

/**
 * Check version compatibility between TypeScript and Python CLI
 */
export async function checkVersions(): Promise<VersionInfo> {
 const tsVersion = require("../../package.json").version;

 try {
 const { stdout } = await execa("python", ["-m", "cihub", "--version"]);
 const pyVersion = stdout.trim().replace("cihub ", "");

 // Semantic version compatibility check
 const [tsMajor, tsMinor] = tsVersion.split(".").map(Number);
 const [pyMajor, pyMinor] = pyVersion.split(".").map(Number);

 const compatible = tsMajor === pyMajor && tsMinor >= pyMinor;

 return {
 typescript: tsVersion,
 python: pyVersion,
 compatible,
 message: compatible
 ? undefined
 : `Version mismatch: TypeScript CLI ${tsVersion} may not be compatible with Python CLI ${pyVersion}`,
 };
 } catch (error) {
 return {
 typescript: tsVersion,
 python: "unknown",
 compatible: false,
 message: "Python CLI not found. Install with: pip install cihub",
 };
 }
}

/**
 * Health check for Python CLI
 */
export async function healthCheck(): Promise<boolean> {
 try {
 const { exitCode } = await execa("python", ["-m", "cihub", "--help"], {
 timeout: 5000,
 reject: false,
 });
 return exitCode === 0;
 } catch {
 return false;
 }
}
```

### 19.5 Startup Checks

```typescript
// src/startup.ts
import { checkVersions, healthCheck } from "./lib/version";
import { Box, Text } from "ink";
import React from "react";

export async function runStartupChecks(): Promise<StartupResult> {
 const errors: string[] = [];
 const warnings: string[] = [];

 // Check Python CLI is available
 const healthy = await healthCheck();
 if (!healthy) {
 errors.push("Python CLI (cihub) not found. Install with: pip install cihub");
 }

 // Check version compatibility
 const versions = await checkVersions();
 if (!versions.compatible && versions.message) {
 warnings.push(versions.message);
 }

 return {
 ok: errors.length === 0,
 errors,
 warnings,
 versions,
 };
}

interface StartupResult {
 ok: boolean;
 errors: string[];
 warnings: string[];
 versions: VersionInfo;
}
```

---

## Appendix D: Wizard Conditional Logic

This appendix details the **conditional step logic** for the interactive wizard.

### D.1 Step Dependencies

```typescript
// src/lib/wizard-steps.ts

interface WizardStep {
 id: string;
 type: "text" | "select" | "confirm";
 question: string;
 key: string;
 default?: string | boolean;
 choices?: string[];
 condition?: (config: WizardConfig) => boolean; // Show step only if true
}

/**
 * All wizard steps with conditional logic
 */
export const WIZARD_STEPS: WizardStep[] = [
 // === Repository Details (always shown) ===
 { id: "repo.owner", type: "text", question: "Repo owner (org/user):", key: "repo.owner" },
 { id: "repo.name", type: "text", question: "Repo name:", key: "repo.name" },
 { id: "repo.use_central", type: "confirm", question: "Use central runner?", key: "repo.use_central_runner", default: true },
 { id: "repo.repo_side", type: "confirm", question: "Enable repo-side execution?", key: "repo.repo_side_execution", default: false },

 // === Language Selection (always shown) ===
 { id: "language", type: "select", question: "Select language:", key: "language", choices: ["java", "python"] },

 // === Python Version (only if language === "python") ===
 {
 id: "python.version",
 type: "select",
 question: "Python version:",
 key: "python.version",
 choices: ["3.12", "3.11", "3.10", "3.9"],
 default: "3.12",
 condition: (c) => c.language === "python",
 },

 // === Python Tools (only if language === "python") ===
 {
 id: "python.tools.pytest",
 type: "confirm",
 question: "Enable pytest?",
 key: "python.tools.pytest.enabled",
 default: true,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.ruff",
 type: "confirm",
 question: "Enable ruff (linter)?",
 key: "python.tools.ruff.enabled",
 default: true,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.black",
 type: "confirm",
 question: "Enable black (formatter)?",
 key: "python.tools.black.enabled",
 default: true,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.isort",
 type: "confirm",
 question: "Enable isort (import sorter)?",
 key: "python.tools.isort.enabled",
 default: false,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.mypy",
 type: "confirm",
 question: "Enable mypy (type checker)?",
 key: "python.tools.mypy.enabled",
 default: false,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.bandit",
 type: "confirm",
 question: "Enable bandit (security)?",
 key: "python.tools.bandit.enabled",
 default: true,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.pip_audit",
 type: "confirm",
 question: "Enable pip-audit (dependency audit)?",
 key: "python.tools.pip_audit.enabled",
 default: true,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.mutmut",
 type: "confirm",
 question: "Enable mutmut (mutation testing)?",
 key: "python.tools.mutmut.enabled",
 default: false,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.hypothesis",
 type: "confirm",
 question: "Enable hypothesis (property testing)?",
 key: "python.tools.hypothesis.enabled",
 default: false,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.semgrep",
 type: "confirm",
 question: "Enable semgrep (SAST)?",
 key: "python.tools.semgrep.enabled",
 default: false,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.trivy",
 type: "confirm",
 question: "Enable trivy (container scanner)?",
 key: "python.tools.trivy.enabled",
 default: true,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.codeql",
 type: "confirm",
 question: "Enable codeql (code analysis)?",
 key: "python.tools.codeql.enabled",
 default: false,
 condition: (c) => c.language === "python",
 },
 {
 id: "python.tools.docker",
 type: "confirm",
 question: "Enable docker builds?",
 key: "python.tools.docker.enabled",
 default: false,
 condition: (c) => c.language === "python",
 },

 // === Java Build Tool (only if language === "java") ===
 {
 id: "java.build_tool",
 type: "select",
 question: "Build tool:",
 key: "java.build_tool",
 choices: ["maven", "gradle"],
 default: "maven",
 condition: (c) => c.language === "java",
 },

 // === Java Version (only if language === "java") ===
 {
 id: "java.version",
 type: "select",
 question: "Java version:",
 key: "java.version",
 choices: ["21", "17", "11", "8"],
 default: "17",
 condition: (c) => c.language === "java",
 },

 // === Java Tools (only if language === "java") ===
 {
 id: "java.tools.junit",
 type: "confirm",
 question: "Enable JUnit tests?",
 key: "java.tools.junit.enabled",
 default: true,
 condition: (c) => c.language === "java",
 },
 {
 id: "java.tools.jacoco",
 type: "confirm",
 question: "Enable JaCoCo coverage?",
 key: "java.tools.jacoco.enabled",
 default: true,
 condition: (c) => c.language === "java",
 },
 {
 id: "java.tools.checkstyle",
 type: "confirm",
 question: "Enable Checkstyle?",
 key: "java.tools.checkstyle.enabled",
 default: true,
 condition: (c) => c.language === "java",
 },
 {
 id: "java.tools.spotbugs",
 type: "confirm",
 question: "Enable SpotBugs?",
 key: "java.tools.spotbugs.enabled",
 default: false,
 condition: (c) => c.language === "java",
 },
 {
 id: "java.tools.owasp",
 type: "confirm",
 question: "Enable OWASP dependency check?",
 key: "java.tools.owasp.enabled",
 default: true,
 condition: (c) => c.language === "java",
 },

 // === Security Tools (always shown) ===
 {
 id: "security.gitleaks",
 type: "confirm",
 question: "Enable gitleaks (secret scanning)?",
 key: "security.gitleaks.enabled",
 default: true,
 },

 // === Thresholds (always shown) ===
 {
 id: "thresholds.coverage",
 type: "text",
 question: "Coverage threshold (%):",
 key: "thresholds.coverage_min",
 default: "80",
 },
 {
 id: "thresholds.max_critical",
 type: "text",
 question: "Max critical vulnerabilities allowed:",
 key: "thresholds.max_critical_vulns",
 default: "0",
 },
];

/**
 * Get filtered steps based on current config
 */
export function getActiveSteps(config: WizardConfig): WizardStep[] {
 return WIZARD_STEPS.filter(step => {
 if (!step.condition) return true;
 return step.condition(config);
 });
}

/**
 * Get next step after current
 */
export function getNextStep(currentId: string, config: WizardConfig): WizardStep | null {
 const activeSteps = getActiveSteps(config);
 const currentIndex = activeSteps.findIndex(s => s.id === currentId);
 if (currentIndex === -1 || currentIndex >= activeSteps.length - 1) {
 return null;
 }
 return activeSteps[currentIndex + 1];
}
```

### D.2 Profile Override

When a profile is selected, it pre-fills wizard answers:

```typescript
// src/lib/profiles.ts

interface Profile {
 name: string;
 description: string;
 answers: Partial<WizardConfig>;
}

export const PROFILES: Profile[] = [
 {
 name: "python-strict",
 description: "Strict Python config: all linters, type checking, mutation testing",
 answers: {
 language: "python",
 python: {
 version: "3.12",
 tools: {
 pytest: { enabled: true },
 ruff: { enabled: true },
 black: { enabled: true },
 isort: { enabled: true },
 mypy: { enabled: true },
 bandit: { enabled: true },
 pip_audit: { enabled: true },
 mutmut: { enabled: true },
 trivy: { enabled: true },
 },
 },
 thresholds: {
 coverage_min: 90,
 mutation_score_min: 80,
 },
 },
 },
 {
 name: "python-minimal",
 description: "Minimal Python config: basic tests and linting",
 answers: {
 language: "python",
 python: {
 version: "3.12",
 tools: {
 pytest: { enabled: true },
 ruff: { enabled: true },
 },
 },
 thresholds: {
 coverage_min: 60,
 },
 },
 },
 {
 name: "java-enterprise",
 description: "Enterprise Java: full security suite, strict coverage",
 answers: {
 language: "java",
 java: {
 build_tool: "maven",
 version: "17",
 tools: {
 junit: { enabled: true },
 jacoco: { enabled: true },
 checkstyle: { enabled: true },
 spotbugs: { enabled: true },
 owasp: { enabled: true },
 },
 },
 security: {
 gitleaks: { enabled: true },
 },
 thresholds: {
 coverage_min: 85,
 max_critical_vulns: 0,
 },
 },
 },
];

/**
 * Apply profile to wizard config
 */
export function applyProfile(profileName: string, config: WizardConfig): WizardConfig {
 const profile = PROFILES.find(p => p.name === profileName);
 if (!profile) {
 throw new Error(`Unknown profile: ${profileName}`);
 }
 return deepMerge(config, profile.answers);
}
```

---

## Appendix E: AI Command Specifications (Legacy)

> **WARNING: DEPRECATED:** This section is superseded by **Part 9: Modular AI Architecture**.
>
> The simpler approach puts AI in the Python CLI (`cihub/ai/` module) with a single `--ai` flag.
> TypeScript just passes the flag through - no complex AI command implementations needed in TypeScript.
>
> **New approach:**
> ```bash
> cihub triage --ai # AI enhances triage results
> cihub check --ai # AI explains check failures
> CIHUB_DEV_MODE=1 cihub ... # Auto-enable AI for debugging
> ```
>
> This section is kept for reference only.

This appendix provides **detailed specifications** for all AI-powered commands.

### E.1 /ai Command

**Purpose:** Free-form AI query about CI/CD state

**Input:** Natural language prompt
**Output:** AI response with optional tool calls

```typescript
// src/commands/ai.ts
import { runAI } from "../lib/ai-client";
import { runCihub } from "../lib/cihub";
import type { CommandHandler } from "../types/commands";

export const aiCommand: CommandHandler = {
 name: "ai",
 description: "Ask AI about your CI/CD",
 usage: "/ai <prompt>",
 examples: [
 "/ai why is my build failing?",
 "/ai how can I speed up my CI?",
 "/ai explain the coverage report",
 ],

 async execute(args: string[], context: CommandContext): Promise<CommandResult> {
 const prompt = args.join(" ");
 if (!prompt) {
 return {
 exit_code: 1,
 summary: "Usage: /ai <your question>",
 problems: [{ severity: "error", message: "No prompt provided" }],
 };
 }

 // Build context from recent results
 const systemPrompt = buildAISystemPrompt(context);

 // Run AI with tool access
 const response = await runAI(prompt, {
 systemPrompt,
 tools: cihubTools,
 cwd: context.cwd,
 lastResult: context.lastResult,
 });

 return {
 exit_code: 0,
 summary: response,
 data: { ai_response: response },
 };
 },
};

function buildAISystemPrompt(context: CommandContext): string {
 return `You are a CI/CD assistant integrated into CIHub.

Current context:
- Working directory: ${context.cwd}
- Last command: ${context.lastResult?.command || "none"}
- Last status: ${context.lastResult?.status || "none"}

You can run cihub commands to gather information:
- Use run_cihub to execute any cihub command
- Use read_artifact to analyze build logs or test results

Be concise and actionable. Provide specific commands the user can run.`;
}
```

### E.2 /explain Command

**Purpose:** Explain the last result or a specific file

```typescript
// src/commands/explain.ts
export const explainCommand: CommandHandler = {
 name: "explain",
 description: "Explain the last result or a specific file",
 usage: "/explain [file]",
 examples: [
 "/explain",
 "/explain pom.xml",
 "/explain .github/workflows/ci.yml",
 ],

 async execute(args: string[], context: CommandContext): Promise<CommandResult> {
 const target = args[0];

 if (target) {
 // Explain specific file
 const fileContent = await readFile(join(context.cwd, target), "utf-8");
 const response = await runAI(
 `Explain this file in the context of CI/CD:\n\n${fileContent}`,
 { cwd: context.cwd }
 );
 return { exit_code: 0, summary: response };
 }

 // Explain last result
 if (!context.lastResult) {
 return {
 exit_code: 1,
 summary: "No previous result to explain. Run a command first.",
 problems: [{ severity: "info", message: "Run /triage or /check first" }],
 };
 }

 const response = await runAI(
 `Explain this CI result in plain terms. What does it mean and what should the user do?\n\n${JSON.stringify(context.lastResult, null, 2)}`,
 { cwd: context.cwd }
 );

 return { exit_code: 0, summary: response };
 },
};
```

### E.3 /diagnose Command

**Purpose:** Deep diagnosis of CI failures

```typescript
// src/commands/diagnose.ts
export const diagnoseCommand: CommandHandler = {
 name: "diagnose",
 description: "Deep diagnosis of CI failures",
 usage: "/diagnose",

 async execute(args: string[], context: CommandContext): Promise<CommandResult> {
 // Step 1: Gather all evidence
 const triage = await runCihub("triage", ["--detect-flaky"], context.cwd);
 const check = await runCihub("check", [], context.cwd);

 // Step 2: Ask AI to synthesize
 const response = await runAI(
 `Diagnose these CI results. Identify:
1. Root cause of failures
2. Whether failures are flaky or deterministic
3. Priority order for fixes
4. Specific fix suggestions

Triage result:
${JSON.stringify(triage, null, 2)}

Check result:
${JSON.stringify(check, null, 2)}`,
 { cwd: context.cwd }
 );

 return {
 exit_code: 0,
 summary: response,
 data: {
 triage_summary: triage.summary,
 check_summary: check.summary,
 diagnosis: response,
 },
 };
 },
};
```

### E.4 /fix Command

**Purpose:** Generate and optionally apply fixes

```typescript
// src/commands/fix.ts
export const fixCommand: CommandHandler = {
 name: "fix",
 description: "Suggest and apply fixes",
 usage: "/fix [issue] [--apply]",
 examples: [
 "/fix",
 "/fix CVE-2024-1234",
 "/fix --apply",
 ],

 async execute(args: string[], context: CommandContext): Promise<CommandResult> {
 const applyMode = args.includes("--apply");
 const issue = args.filter(a => !a.startsWith("--"))[0];

 // Get fix suggestions from AI
 const suggestions = await runAI(
 issue
 ? `Suggest a fix for this issue: ${issue}`
 : `Suggest fixes for the problems in the last command result:\n${JSON.stringify(context.lastResult, null, 2)}`,
 { cwd: context.cwd }
 );

 if (!applyMode) {
 return {
 exit_code: 0,
 summary: suggestions,
 suggestions: [{ message: "Run /fix --apply to apply these fixes" }],
 };
 }

 // Apply mode - confirm with user first
 return {
 exit_code: 0,
 summary: suggestions,
 data: {
 fixes: suggestions,
 awaiting_confirmation: true,
 },
 };
 },
};
```

### E.5 /review Command

**Purpose:** AI code review of recent changes

```typescript
// src/commands/review.ts
export const reviewCommand: CommandHandler = {
 name: "review",
 description: "AI review of recent changes",
 usage: "/review [commit]",
 examples: [
 "/review",
 "/review HEAD~3",
 "/review abc123",
 ],

 async execute(args: string[], context: CommandContext): Promise<CommandResult> {
 const commit = args[0] || "HEAD";

 // Get diff
 const diff = await execGit(["diff", `${commit}^`, commit], context.cwd);

 // Get commit message
 const message = await execGit(["log", "-1", "--format=%B", commit], context.cwd);

 // AI review
 const review = await runAI(
 `Review this commit for:
1. Code quality issues
2. Potential bugs
3. Security concerns
4. CI/CD impact

Commit message: ${message}

Diff:
${diff}`,
 { cwd: context.cwd }
 );

 return {
 exit_code: 0,
 summary: review,
 data: {
 commit,
 review,
 },
 };
 },
};
```

### E.6 Tool Call Safety

All AI tool calls go through a safety layer:

```typescript
// src/lib/ai-safety.ts

const ALLOWED_COMMANDS = [
 "detect", "discover", "triage", "check", "verify",
 "report", "docs", "adr", "config", "hub-ci",
];

const DANGEROUS_FLAGS = [
 "--apply", // Applies changes
 "--force", // Forces operations
 "--delete", // Deletes files
];

export function validateToolCall(
 toolName: string,
 input: Record<string, unknown>
): { allowed: boolean; reason?: string } {
 if (toolName !== "run_cihub") {
 return { allowed: true };
 }

 const command = input.command as string;
 const args = (input.args as string[]) || [];

 // Check command is allowed
 const baseCommand = command.split(" ")[0];
 if (!ALLOWED_COMMANDS.includes(baseCommand)) {
 return {
 allowed: false,
 reason: `Command '${baseCommand}' not in allowlist`
 };
 }

 // Check for dangerous flags
 for (const flag of DANGEROUS_FLAGS) {
 if (args.includes(flag)) {
 return {
 allowed: false,
 reason: `Flag '${flag}' requires user confirmation`
 };
 }
 }

 return { allowed: true };
}
```
