## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Deployment Boundary (Required)

- `wepp.cloud` infrastructure (`wepp1`, `wepp2`, and `wepp3`) uses Docker
  Compose with host-local builds. Its canonical entry point is
  `scripts/deploy-production.sh`, selected by the installed `wctl` preset.
- `openwepp.org` uses Kubernetes. Registry-published images, manifest digests,
  and GitOps/Kubernetes procedures belong only to that deployment.
- Never require a container registry for a `wepp.cloud` deployment or recovery.
- Before changing a deployment or rollback runbook, read
  `scripts/deploy-production.sh` and preserve its pull, build, topology,
  Redis, static-asset, health-check, and cleanup contracts. Do not replace it
  with ad hoc `docker compose` commands unless the user explicitly requests a
  bounded diagnostic action.

There are three Docker Compose deployments of the full app and a dedicated
production worker deployment.

## development
- host: forest.bearhive.internal 
- domain: wc.bearhive.duckdns.org
- docker-compose.dev.yml

## test production
- host: forest1.bearhive.internal 
- domain: wc-prod.bearhive.duckdns.org
- docker-compose.prod.yml

## production
- host: wepp1
- domain: wepp.cloud

## production worker
- host: wepp2
- deployment family: wepp.cloud Docker Compose

## production fork/archive worker
- host: wepp3
- compose source: `docker-compose.prod.wepp3.yml`
- scope: `rq-worker-fork-archive` only; no other containers
- contract: `docs/work-packages/20260803_fork_archive_serial_queue/package.md`

## Kubernetes
- domain: openwepp.org
- deployment model: Kubernetes with registry-published images
- do not reuse this model for wepp.cloud hosts
