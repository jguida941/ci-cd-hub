DR_REPORT ?= $(DR_DIR)/dr-report.json
DR_EVENTS ?= $(DR_DIR)/dr-events.ndjson

.PHONY: run-dr clean-dr
run-dr: ## Run the DR drill simulator
	mkdir -p "$(DR_DIR)"
	$(PYTHON) tools/run_dr_drill.py \
		--output "$(DR_REPORT)" \
		--ndjson "$(DR_EVENTS)"

clean-dr: ## Remove DR drill artifacts
	rm -rf "$(DR_DIR)"
