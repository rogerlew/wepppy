## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

There are 3 deployments of the full docker app and one planned dedicated
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

## production fork/archive worker (planned)
- host: wepp3
- compose source: `docker-compose.prod.worker.yml`
- scope: opt-in `rq-worker-fork-archive` only; no other containers
- contract: `docs/work-packages/20260803_fork_archive_serial_queue/package.md`
