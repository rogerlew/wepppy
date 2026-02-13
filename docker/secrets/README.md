# Docker Compose Secrets

This directory is intentionally kept out of git. Populate one file per secret ID
and mount them via Docker Compose `secrets:` to `/run/secrets/<secret_id>`.

Required secrets vary by stack (dev/prod/worker). The canonical inventory and
IDs live in `docs/infrastructure/secrets.md`.

Notes:
- Keep files mode `0600` on the host.
- Do not store secrets under `/wc1` or any browseable/exportable directory.
