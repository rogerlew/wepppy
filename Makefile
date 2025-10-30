.PHONY: help deploy-nuc2 ci-dryrun prod-workers-up prod-workers-down prod-workers-scale prod-workers-logs

# Defaults (override on command line, e.g., `make ci-dryrun NUC1=dev-a`)
ENV_FILE ?= docker/.env
WITH_CAO ?= 1
NUC1 ?= nuc1.local
NUC2 ?= nuc2.local
NUC3 ?= nuc3.local
REPO ?= /workdir/wepppy
WC1 ?= /wc1
LOOPS ?= 10
SCOPE ?=
HOST ?= nuc2.local
RQ_REDIS_URL ?=
COUNT ?= 2

help:
	@echo "Targets:"
	@echo "  deploy-nuc2      Install deps, prepare /wc1, clone repos, setup wctl; optional CAO"
	@echo "  ci-dryrun        Run triage on $(NUC1), validate on $(NUC2), flake loop on $(NUC3)"
	@echo "  prod-workers-up  Start rq-worker on HOST with RQ_REDIS_URL"
	@echo "  prod-workers-down Stop rq-worker on HOST"
	@echo "  prod-workers-scale Scale rq-worker to COUNT on HOST"
	@echo "  prod-workers-logs  Tail worker logs on HOST"
	@echo ""
	@echo "Variables:"
	@echo "  ENV_FILE=$(ENV_FILE)  WITH_CAO=$(WITH_CAO)  NUC1=$(NUC1) NUC2=$(NUC2) NUC3=$(NUC3)"
	@echo "  REPO=$(REPO) WC1=$(WC1) LOOPS=$(LOOPS) SCOPE=$(SCOPE:[--nodb-only|--wepp-only])"
	@echo "  HOST=$(HOST) RQ_REDIS_URL=$(RQ_REDIS_URL) COUNT=$(COUNT)"

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

prod-workers-up:
	@if [ -z "$(RQ_REDIS_URL)" ]; then \
		echo "Error: RQ_REDIS_URL is required, e.g. redis://forest1:6379/9"; exit 1; \
	fi
	@echo "==> Starting rq-worker on $(HOST) with RQ_REDIS_URL=$(RQ_REDIS_URL)"
	ssh $(HOST) "cd $(REPO) && RQ_REDIS_URL='$(RQ_REDIS_URL)' docker compose --env-file docker/.env -f docker/docker-compose.prod.yml up -d rq-worker"

prod-workers-down:
	@echo "==> Stopping rq-worker on $(HOST)"
	ssh $(HOST) "cd $(REPO) && docker compose --env-file docker/.env -f docker/docker-compose.prod.yml stop rq-worker || true"

prod-workers-scale:
	@if [ -z "$(RQ_REDIS_URL)" ]; then \
		echo "Note: RQ_REDIS_URL not set; using value from docker/.env on remote if present"; \
	fi
	@echo "==> Scaling rq-worker to $(COUNT) on $(HOST)"
	ssh $(HOST) "cd $(REPO) && RQ_REDIS_URL='$(RQ_REDIS_URL)' docker compose --env-file docker/.env -f docker/docker-compose.prod.yml up -d --scale rq-worker=$(COUNT) rq-worker"

prod-workers-logs:
	@echo "==> Tailing rq-worker logs on $(HOST) (Ctrl-C to exit)"
	ssh -t $(HOST) "cd $(REPO) && docker compose --env-file docker/.env -f docker/docker-compose.prod.yml logs -f rq-worker"
