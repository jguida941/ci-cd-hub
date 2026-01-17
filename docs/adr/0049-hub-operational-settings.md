# ADR-0049: Hub Operational Settings (Config-File-First)

**Status**: Accepted  
**Date:** 2026-01-06  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-06  

## Context

Hub-internal workflows (`hub-run-all.yml`, `hub-orchestrator.yml`) have accumulated many boolean inputs for operational settings:
- `skip_mutation`, `write_github_summary`, `include_details` (execution)
- `cihub_debug`, `cihub_verbose`, `cihub_debug_context`, `cihub_emit_triage` (debug)
- `harden_runner_policy` (security)

**Problems:**
1. **No persistent state** - Changing default behavior required editing workflow YAML
2. **Inconsistent patterns** - Some settings were inputs, others were env vars
3. **Scalability concern** - Adding more toggles increases workflow complexity
4. **Manual editing risk** - Users had to edit workflow files to change defaults

**Note:** This is separate from per-repo tool configs (`config/repos/*.yaml`, `.ci-hub.yml`) covered in ADR-0002 and ADR-0024. This ADR addresses hub-wide operational settings that control HOW the hub runs, not WHAT it runs on repos.

## Decision

Adopt a **config-file-first** pattern for hub operational settings:

### 1. Config File: `cihub/data/config/hub-settings.yaml`

```yaml
execution:
 skip_mutation: false
 write_github_summary: true
 include_details: true

debug:
 enabled: false
 verbose: false
 debug_context: false
 emit_triage: false

security:
 harden_runner:
 policy: audit # audit | block | disabled
```

### 2. CLI Commands: `cihub hub config`

```bash
# View current settings
cihub hub config show

# Change a setting
cihub hub config set debug.enabled true

# Load settings for GitHub Actions
cihub hub config load --github-output
```

### 3. Workflow Integration

Hub-internal workflows use a `load-settings` job that calls the CLI with override arguments:

```yaml
# Single CLI call - no inline scripting (per AGENTS.md: "Never write inline scripts in YAML")
- name: Load Hub Settings
 id: resolve
 run: cihub hub config load --github-output \
 --override-skip-mutation "${{ inputs.skip_mutation }}" \
 --override-debug "${{ inputs.cihub_debug }}" \
 --override-harden-runner-policy "${{ inputs.harden_runner_policy }}"
```

The CLI:
1. Loads config file values from `cihub/data/config/hub-settings.yaml`
2. Applies non-empty override arguments (empty strings are ignored)
3. Writes resolved values to `GITHUB_OUTPUT`

**Precedence (highest wins):**
```
CLI --override-* args → cihub/data/config/hub-settings.yaml → built-in defaults
```

### 4. Workflow Input Changes

Inputs change from boolean with defaults to string with empty default:

```yaml
# Before (boolean with default)
skip_mutation:
 type: boolean
 default: false

# After (override input)
skip_mutation:
 description: 'Override: Skip mutation testing'
 type: string
 default: '' # Empty = use config file value
```

This makes the dispatch UI cleaner - inputs only appear when you want to override.

## Alternatives Considered

1. **Keep all settings as workflow inputs:**
 Rejected. No persistent state; requires editing YAML for default changes.

2. **Use GitHub repository variables:**
 Rejected. Requires GitHub UI or API for changes; not version-controlled.

3. **Merge with per-repo config files:**
 Rejected. Hub operational settings are fundamentally different from per-repo tool configs.

4. **Environment file (.env):**
 Rejected. Not YAML; harder to validate; different pattern from repo configs.

## Consequences

**Positive:**
- Settings are version-controlled and reviewable
- CLI provides easy viewing and editing
- Workflow inputs become pure overrides for one-off runs
- Same YAML pattern as repo configs (familiar to users)
- Schema validation via `cihub/data/schema/hub-settings.schema.json`
- Scalable - adding new settings doesn't increase workflow complexity

**Negative:**
- Extra job in workflows for config loading (~10s overhead)
- Two places to check when debugging (config file + input overrides)
- Sparse checkout required for fast config loading

## Implementation

### Files Created

| File | Purpose |
|------|---------|
| `cihub/data/config/hub-settings.yaml` | Hub operational settings |
| `cihub/data/schema/hub-settings.schema.json` | Validation schema |
| `cihub/commands/hub_config.py` | CLI command implementation |
| `cihub/cli_parsers/hub.py` | CLI parser for hub commands |

### Workflows Updated

- `.github/workflows/hub-run-all.yml` - Added `load-settings` job
- `.github/workflows/hub-orchestrator.yml` - Added `load-settings` job

### Config Hierarchy (Complete Picture)

```
Hub Operational Settings (this ADR):
 cihub/data/config/hub-settings.yaml → controls HOW hub runs

Per-Repo Tool Configs (ADR-0002, ADR-0024):
 1. .ci-hub.yml (repo-local)
 2. config/repos/<repo>.yaml (hub-side)
 3. config/defaults.yaml (global)
 → controls WHAT runs on each repo
```

## Migration

Existing workflows continue to work. The `load-settings` job uses built-in defaults if `cihub/data/config/hub-settings.yaml` doesn't exist. To opt-in to config-file-first:

1. Create `cihub/data/config/hub-settings.yaml` (or use CLI: `cihub hub config set`)
2. Commit the file
3. Future runs will use the config file values by default

## References

- ADR-0002: Config Precedence Hierarchy (per-repo configs)
- ADR-0024: Workflow Dispatch Input Limit
- GitHub Actions: [workflow_dispatch event](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
