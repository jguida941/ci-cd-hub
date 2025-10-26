REKOR_DIGEST ?=
REKOR_SUBJECT ?= ghcr.io/example/app
REKOR_OUTPUT ?= $(EVIDENCE_DIR)/rekor

.PHONY: run-rekor-monitor
run-rekor-monitor: ## Fetch Rekor inclusion data (set REKOR_DIGEST=sha256:<digest>)
	@if [ -z "$(REKOR_DIGEST)" ]; then \
		echo "Set REKOR_DIGEST=sha256:<digest> before running run-rekor-monitor"; \
		exit 1; \
	fi
	mkdir -p "$(REKOR_OUTPUT)"
	./tools/rekor_monitor.sh "$(REKOR_DIGEST)" "$(REKOR_SUBJECT)" "$(REKOR_OUTPUT)"
