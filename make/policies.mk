KYVERNO_DEPLOY_FLAGS ?=
KYVERNO_VERIFY_FLAGS ?=
KYVERNO_VERIFY_NAMESPACE ?= kyverno-verify
KYVERNO_EVIDENCE_DIR ?= artifacts/evidence/kyverno

.PHONY: kyverno/deploy
kyverno/deploy: ## Apply Kyverno ClusterPolicies to the target cluster (requires kubectl access)
	@if [ -z "$(KUBECTL_CONTEXT)" ]; then echo "KUBECTL_CONTEXT must be set (e.g. export KUBECTL_CONTEXT=prod-cluster)"; exit 1; fi
	KUBECTL_CONTEXT="$(KUBECTL_CONTEXT)" ./scripts/deploy_kyverno.sh --context "$(KUBECTL_CONTEXT)" $(KYVERNO_DEPLOY_FLAGS)

.PHONY: kyverno/verify
kyverno/verify: ## Exercise policies against fixtures on the live cluster to capture enforcement evidence
	@if [ -z "$(KUBECTL_CONTEXT)" ]; then echo "KUBECTL_CONTEXT must be set (e.g. export KUBECTL_CONTEXT=prod-cluster)"; exit 1; fi
	KUBECTL_CONTEXT="$(KUBECTL_CONTEXT)" ./scripts/verify_kyverno_enforcement.sh --cluster --context "$(KUBECTL_CONTEXT)" --namespace "$(KYVERNO_VERIFY_NAMESPACE)" $(KYVERNO_VERIFY_FLAGS) "$(KYVERNO_EVIDENCE_DIR)"
