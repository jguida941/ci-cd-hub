CHAOS_CONFIG ?= chaos/chaos-fixture.json
CHAOS_OUTPUT ?= $(CHAOS_DIR)/report.json
CHAOS_NDJSON ?= $(CHAOS_DIR)/events.ndjson

.PHONY: run-chaos clean-chaos
run-chaos: ## Execute the chaos simulator locally
	@test -f "$(CHAOS_CONFIG)" || { echo "Missing $(CHAOS_CONFIG)"; exit 1; }
	mkdir -p "$(CHAOS_DIR)"
	$(PYTHON) tools/run_chaos.py \
		--config "$(CHAOS_CONFIG)" \
		--output "$(CHAOS_OUTPUT)" \
		--ndjson "$(CHAOS_NDJSON)"

clean-chaos: ## Remove generated chaos artifacts
	rm -rf "$(CHAOS_DIR)"
