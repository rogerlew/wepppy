# Docker Compose Secrets

This directory is intentionally kept out of git. Populate one file per secret ID
and mount them via Docker Compose `secrets:` to `/run/secrets/<secret_id>`.

Required secrets vary by stack (dev/prod/worker). The canonical inventory and
IDs live in `docs/infrastructure/secrets.md`.

Notes:
- Keep files mode `0600` on the host.
- Do not store secrets under `/wc1` or any browseable/exportable directory.
- CAP is the exception to a mode-only rule: it runs as UID `10001`, so
  `cap_secret` also needs named-user read ACLs for every effective consumer.
  Repair a same-value inode or install it while consumers are stopped with
  `docker/install-cap-secret.sh < /secure/operator/source`; do not overwrite it
  directly because replacement inodes do not retain ACLs. The helper refuses
  a live value rotation; use the coordinated stop/install/deploy runbook.

Smoke/axe local auth convention:
- Preferred file: `dev-agent.env`
  - Expected keys:
    - `DEV_AGENT_EMAIL`
    - `DEV_AGENT_PASSWORD`
    - `SMOKE_AGENT_EMAIL`
    - `SMOKE_AGENT_PASSWORD`
- Legacy compatibility file: `ally-agent-smoke.env`
  - Expected keys:
    - `ALLY_AGENT_EMAIL`
    - `ALLY_AGENT_PASSWORD`
