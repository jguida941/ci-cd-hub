GRYPE_REPORT ?= fixtures/supply_chain/grype-report.sample.json
VULN_OUTPUT ?= $(POLICY_INPUTS_DIR)/vulnerabilities.json
VEX_INPUT ?= $(SBOM_DIR)/app.vex.json

.PHONY: build-vuln-input
build-vuln-input: build-vex ## Produce policy input JSON from the sample Grype report
	@test -f "$(GRYPE_REPORT)" || { echo "Missing $(GRYPE_REPORT)"; exit 1; }
	mkdir -p "$(POLICY_INPUTS_DIR)"
	$(PYTHON) tools/build_vuln_input.py \
		--grype-report "$(GRYPE_REPORT)" \
		--output "$(VULN_OUTPUT)" \
		--cvss-threshold 7.0 \
		--epss-threshold 0.7 \
		--vex "$(VEX_INPUT)"
