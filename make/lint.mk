.PHONY: lint lint-markdown
lint: lint-markdown ## Run the full lint suite

lint-markdown: ## Lint Markdown files with markdownlint
	$(MARKDOWNLINT) "**/*.md"
