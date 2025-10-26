.PHONY: test test-tools
test: test-tools ## Run every available test suite

test-tools: ## Execute pytest for tools/ modules
	$(PYTHON) -m pytest tools/tests
