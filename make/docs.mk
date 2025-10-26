.PHONY: docs docs-build docs-serve
docs: docs-build ## Build the MkDocs site

docs-build: ## Build the docs site into site/
	$(MKDOCS) build --config-file docs/mkdocs.yml

docs-serve: ## Serve docs locally with live reload
	$(MKDOCS) serve --config-file docs/mkdocs.yml
