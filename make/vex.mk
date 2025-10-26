VEX_CONFIG ?= fixtures/supply_chain/vex_exemptions.json
VEX_OUTPUT ?= $(SBOM_DIR)/app.vex.json

.PHONY: build-vex
build-vex: ## Generate a CycloneDX VEX from sample exemptions
	@test -f "$(VEX_CONFIG)" || { echo "Missing $(VEX_CONFIG)"; exit 1; }
	mkdir -p "$(SBOM_DIR)"
	$(PYTHON) tools/generate_vex.py \
		--config "$(VEX_CONFIG)" \
		--output "$(VEX_OUTPUT)" \
		--subject ghcr.io/example/app@sha256:$$(printf 'a%.0s' $$(seq 64)) \
		--manufacturer ExampleCo \
		--product demo-app
