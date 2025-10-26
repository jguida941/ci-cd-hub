CACHE_SENTINEL_CACHE_DIR ?= fixtures/cache_sentinel/sample-cache
CACHE_SENTINEL_EVIDENCE_DIR ?= $(EVIDENCE_DIR)/cache
CACHE_SENTINEL_MANIFEST ?= $(CACHE_SENTINEL_EVIDENCE_DIR)/cache-manifest.json
CACHE_SENTINEL_REPORT ?= $(CACHE_SENTINEL_EVIDENCE_DIR)/cache-report.json
CACHE_SENTINEL_QUARANTINE ?= $(CACHE_SENTINEL_EVIDENCE_DIR)/quarantine
CACHE_SENTINEL_MAX_FILES ?= 500

.PHONY: cache-sentinel-record cache-sentinel-verify run-cache-sentinel
cache-sentinel-record: ## Capture a cache manifest from the sample cache directory
	@test -d "$(CACHE_SENTINEL_CACHE_DIR)" || { echo "Missing $(CACHE_SENTINEL_CACHE_DIR)"; exit 1; }
	mkdir -p "$(CACHE_SENTINEL_EVIDENCE_DIR)"
	$(PYTHON) tools/cache_sentinel.py record \
		--cache-dir "$(CACHE_SENTINEL_CACHE_DIR)" \
		--output "$(CACHE_SENTINEL_MANIFEST)" \
		--max-files "$(CACHE_SENTINEL_MAX_FILES)"

cache-sentinel-verify: cache-sentinel-record ## Verify cache manifest integrity
	$(PYTHON) tools/cache_sentinel.py verify \
		--cache-dir "$(CACHE_SENTINEL_CACHE_DIR)" \
		--manifest "$(CACHE_SENTINEL_MANIFEST)" \
		--quarantine-dir "$(CACHE_SENTINEL_QUARANTINE)" \
		--report "$(CACHE_SENTINEL_REPORT)"

run-cache-sentinel: cache-sentinel-record cache-sentinel-verify ## Run record + verify steps sequentially
	@echo "Cache Sentinel artifacts written to $(CACHE_SENTINEL_EVIDENCE_DIR)"
