# Dispatch Setup (Reusable Workflows)

Use this guide to enable cross-repo dispatch from the hub orchestrator.

## When to use dispatch
- Target repos already have a `workflow_dispatch` workflow that calls the reusable `java-ci.yml` or `python-ci.yml`.
- You need the target repo’s runners/secrets or prefer repo-owned CI.
- If a repo is central-only (no workflows), set `repo.dispatch_enabled: false` in its hub config.

## Create a token (PAT)
1. Go to GitHub → Settings → Developer settings → Personal access tokens.
2. Classic PAT (simple): Generate new token (classic) → scopes: check `repo` and `workflow`.
   Fine-grained PAT (stricter):
   - Resource owner: your account
   - Repository access: include `ci-hub-orchestrator` and all target repos
   - Permissions: Actions Read/Write, Contents Read, Metadata Read
3. Generate and copy the token.

## Add the secret to the hub repo
- GitHub UI: `ci-hub-orchestrator` → Settings → Secrets and variables → Actions → New repository secret → Name `HUB_DISPATCH_TOKEN` → paste token.
- CLI: `gh secret set HUB_DISPATCH_TOKEN -R jguida941/ci-hub-orchestrator`

## Configure repos
- Hub config: set `repo.dispatch_enabled: false` for central-only repos (e.g., fixtures). Default is true.
- Dispatchable repos must have a workflow with `workflow_dispatch` that calls the reusable workflow and accepts inputs (including `workdir` for monorepos).
- Use `repo.run_group` (full/fixtures/smoke) and the `run_group` workflow input to limit which configs the hub runs.

## Artifact naming
- Orchestrator uploads artifacts with repo-specific names to avoid collisions; keep unique names if adding artifacts.

## Troubleshooting
- `Resource not accessible by integration`: token lacks `actions:write`/`contents:read` on target repo.
- `404 workflow`: target repo has no dispatchable workflow.
- Artifact `409 Conflict`: artifacts are now named with repo/run id; keep names unique if adding more.
- Multiple entries for same repo: hub-run-all and orchestrator include `config_basename` and `subdir` in job/artifact names to disambiguate when multiple configs point to the same repo.
