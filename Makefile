.DEFAULT_GOAL := help

COMMON_MAKEFILE := make/common.mk
ifneq ($(wildcard $(COMMON_MAKEFILE)),)
include $(COMMON_MAKEFILE)
endif

MAKEFILES := $(filter-out $(COMMON_MAKEFILE),$(wildcard make/*.mk))
ifneq ($(strip $(MAKEFILES)),)
include $(MAKEFILES)
endif

.PHONY: help list-targets
help: ## Show common targets sourced from make/*.mk files
	@echo "Usage: make <target>"
	@echo ""
	@grep -hE '^[[:alnum:]_/.-]+:.*##' $(MAKEFILES) 2>/dev/null | \
		awk 'BEGIN {FS=":.*##"} {printf "  %-24s %s\n", $$1, $$2}'

list-targets: ## Print every available target (debug helper)
	@grep -hE '^[[:alnum:]_/.-]+:' $(MAKEFILES) 2>/dev/null | \
		cut -d':' -f1 | sort -u
