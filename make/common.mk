# Shared defaults for local automation

PYTHON ?= $(shell command -v python 2>/dev/null)
ifeq ($(PYTHON),)
PYTHON := $(shell command -v python3 2>/dev/null)
endif
ifeq ($(PYTHON),)
PYTHON := python3
endif

PIP ?= $(shell command -v pip 2>/dev/null)
ifeq ($(PIP),)
PIP := $(shell command -v pip3 2>/dev/null)
endif
ifeq ($(PIP),)
PIP := pip3
endif
MKDOCS ?= mkdocs
MARKDOWNLINT ?= ./scripts/run_markdownlint.sh

ARTIFACTS_DIR ?= artifacts
SBOM_DIR ?= $(ARTIFACTS_DIR)/sbom
POLICY_INPUTS_DIR ?= $(ARTIFACTS_DIR)/policy-inputs
EVIDENCE_DIR ?= $(ARTIFACTS_DIR)/evidence
MUTATION_DIR ?= $(ARTIFACTS_DIR)/mutation
CHAOS_DIR ?= $(ARTIFACTS_DIR)/chaos
DR_DIR ?= $(ARTIFACTS_DIR)/dr
