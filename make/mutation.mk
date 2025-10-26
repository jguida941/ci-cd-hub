MUTATION_CONFIG ?= mutation-observatory.ci.yaml
MUTATION_JSON ?= $(MUTATION_DIR)/run.json
MUTATION_NDJSON ?= $(MUTATION_DIR)/run.ndjson
MUTATION_SUMMARY ?= $(MUTATION_DIR)/summary.md

.PHONY: run-mutation clean-mutation
run-mutation: ## Run Mutation Observatory locally with repo config
	@test -f "$(MUTATION_CONFIG)" || { echo "Missing $(MUTATION_CONFIG)"; exit 1; }
	mkdir -p "$(MUTATION_DIR)"
	$(PYTHON) tools/mutation_observatory.py \
		--config "$(MUTATION_CONFIG)" \
		--output "$(MUTATION_JSON)" \
		--ndjson "$(MUTATION_NDJSON)" \
		--markdown "$(MUTATION_SUMMARY)"

clean-mutation: ## Drop Mutation Observatory artifacts
	rm -rf "$(MUTATION_DIR)"
