MARKDOWNLINT_FILES := $(shell git ls-files '*.md')

.PHONY: lint lint-markdown security-lint bandit-report dbt
lint: lint-markdown security-lint ## Run the full lint suite

lint-markdown: ## Lint Markdown files with markdownlint
	@test -z "$(MARKDOWNLINT_FILES)" || $(MARKDOWNLINT) $(MARKDOWNLINT_FILES)

security-lint: ## Run security static analysis (Ruff S, Bandit, pip-audit, workflow guard)
	@mkdir -p artifacts/security
	$(PYTHON) -m ruff check --select S .
	@echo "[bandit] scanning Python sources (report: artifacts/security/bandit.txt)"
	@$(PYTHON) -m bandit -r tools scripts \
		--configfile .bandit.yaml \
		--format txt \
		--output artifacts/security/bandit.txt \
		--severity-level low \
		--confidence-level low || true
	PIP_AUDIT_PROGRESS_BAR=off $(PYTHON) -m pip_audit -r requirements-dev.txt -r requirements-dev.lock
	$(PYTHON) scripts/check_workflow_integrity.py

bandit-report: ## Run a full Bandit scan (including tests) and write artifacts/security/bandit-full.txt
	@mkdir -p artifacts/security
	@echo "[bandit] generating full repository report (artifacts/security/bandit-full.txt)"
	@$(PYTHON) -m bandit -r . \
		--configfile .bandit.full.yaml \
		--format txt \
		--output artifacts/security/bandit-full.txt \
		--severity-level low \
		--confidence-level low || true

dbt: ## Run dbt build with repo defaults
	$(PYTHON) scripts/run_dbt.py build
