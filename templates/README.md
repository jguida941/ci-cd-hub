# Templates Overview

Quick reference for templates.

- **Repo template:** `templates/repo/.ci-hub.yml` – drop into target repo for local overrides.
- **Hub config template:** `templates/hub/config/repos/repo-template.yaml` – starting point for hub-side per-repo config.
- **Profiles:** `templates/profiles/*.yaml` – fast/quality/security plus new minimal, compliance, and coverage-gate variants for Java and Python.
  - Hub config lives in `config/repos/` (in this repo).
  - Repo-local overrides live in `.ci-hub.yml` (inside each target repo).

## How to use profiles quickly

```bash
# 1) Pick a profile
ls templates/profiles

# 2) Merge it into a repo config (creates file if missing)
python scripts/apply_profile.py templates/profiles/python-fast.yaml config/repos/my-repo.yaml

# 3) Edit repo metadata (owner/name/language/subdir)
$EDITOR config/repos/my-repo.yaml

# 4) Validate
python scripts/validate_config.py config/repos/my-repo.yaml
```

Profiles are additive and can be re-applied; existing repo-specific overrides win over profile defaults.
