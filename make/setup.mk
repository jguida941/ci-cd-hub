.PHONY: setup
setup: ## Install Python tooling for local runs
	$(PIP) install -r requirements-dev.txt
	@if [ -f requirements-dev.lock ]; then \
		$(PIP) install -r requirements-dev.lock; \
	fi
