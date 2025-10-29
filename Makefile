.PHONY: help deploy-nuc2 ci-dryrun

# Defaults (override on command line, e.g., `make ci-dryrun NUC1=dev-a`)
ENV_FILE ?= docker/.env
WITH_CAO ?= 1
NUC1 ?= nuc1
NUC2 ?= nuc2
NUC3 ?= nuc3
REPO ?= /workdir/wepppy
WC1 ?= /wc1
LOOPS ?= 10
SCOPE ?=

help:
	@echo "Targets:"
	@echo "  deploy-nuc2      Install deps, prepare /wc1, clone repos, setup wctl; optional CAO"
	@echo "  ci-dryrun        Run triage on $(NUC1), validate on $(NUC2), flake loop on $(NUC3)"
	@echo ""
	@echo "Variables:"
	@echo "  ENV_FILE=$(ENV_FILE)  WITH_CAO=$(WITH_CAO)  NUC1=$(NUC1) NUC2=$(NUC2) NUC3=$(NUC3)"
	@echo "  REPO=$(REPO) WC1=$(WC1) LOOPS=$(LOOPS) SCOPE=$(SCOPE:[--nodb-only|--wepp-only])"

deploy-nuc2:
	@echo "==> Deploying WEPPcloud dev node on this host"
	@if [ $(WITH_CAO) -eq 1 ]; then \
		sudo bash services/cao/scripts/weppcloud_deploy.sh --env-file $(ENV_FILE) --with-cao ; \
	else \
		sudo bash services/cao/scripts/weppcloud_deploy.sh --env-file $(ENV_FILE) ; \
	fi

ci-dryrun:
	@echo "==> Running CI Samurai dry run: $(NUC1) -> $(NUC2) -> $(NUC3)"
	bash services/cao/scripts/ci_samurai_dryrun.sh \
	  --nuc1 $(NUC1) --nuc2 $(NUC2) --nuc3 $(NUC3) \
	  --repo $(REPO) --wc1 $(WC1) --loops $(LOOPS) $(SCOPE)

