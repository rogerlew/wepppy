# CI Samurai Scripts
> 
> Helper scripts for bootstrapping dev runners (NUCs) and running cross-host dry runs for CI Samurai.
> 
> See also: services/cao/ci-samurai.md for the full architecture and workflow.

## Overview

This folder contains two utility scripts:

- `weppcloud_deploy.sh` — Idempotent provisioning for a WEPPcloud dev node (e.g., nuc2). Installs base tooling, prepares `/wc1`, clones repos into `/workdir`, sets up `wctl`, and optionally installs the CAO systemd service.
- `ci_samurai_dryrun.sh` — Orchestrates a CI Samurai dry run across `nuc1`/`nuc2`/`nuc3`: triage on nuc1, validation on nuc2, flake stress on nuc3. Publishes logs under `nuc1:/wc1/ci-samurai/logs/<timestamp>/`.

Both scripts are safe to re-run and designed to be parameterized via flags and environment variables.

Makefile shortcuts (repo root):

```bash
# Show targets and variables
make help

# Provision nuc2 with CAO and .env from docker/.env
make deploy-nuc2 WITH_CAO=1 ENV_FILE=docker/.env

# Dry run across nuc1/nuc2/nuc3 (override hosts as needed)
make ci-dryrun NUC1=nuc1 NUC2=nuc2 NUC3=nuc3 LOOPS=10
```

## Prerequisites

- Ubuntu 24.04 on each NUC with SSH access
- User and group for local ownership, default `roger:docker` (customizable)
- Docker engine is recommended (optional flags let you skip install if already present)
- pfSense handles DuckDNS IP updates (no DuckDNS writes in these scripts)

## Quick Start

Provision nuc2 with local `/wc1` and optional CAO service:

```bash
sudo bash services/cao/scripts/weppcloud_deploy.sh \
  --env-file /path/to/.env \
  --with-cao
```

Run a cross-host dry run using nuc1/nuc2/nuc3 defaults:

```bash
bash services/cao/scripts/ci_samurai_dryrun.sh
```

Start worker-only containers on a remote host pointing at a central Redis (forest1):

```bash
# Example: start on nuc2, connecting to Redis on forest1:6379 DB 9
make prod-workers-up HOST=nuc2.local RQ_REDIS_URL=redis://forest1:6379/9

# Scale to 3 workers on nuc3
make prod-workers-scale HOST=nuc3.local COUNT=3 RQ_REDIS_URL=redis://forest1:6379/9

# Tail logs
make prod-workers-logs HOST=nuc2.local

# Stop workers
make prod-workers-down HOST=nuc2.local
```

## Script: weppcloud_deploy.sh

Purpose: Prepare a dev runner with local `/wc1`, clone/update repos into `/workdir`, install toolchains (uv, rustup, npm globals), and optionally install the CAO systemd service.

- Defaults
  - `WC_ROOT=/wc1`
  - `WORKDIR=/workdir`
  - `OWNER_USER=roger`
  - `OWNER_GROUP=docker`
- What it does
  - Installs packages: git, curl, python3, venv, pip, ripgrep, nfs-common, jq, unzip
  - Installs Docker (unless `--skip-docker`), ensures user in `docker` group
  - Creates `/wc1` and `/wc1/geodata` owned by `roger:docker`
  - Clones/updates repos to `/workdir`: wepppy, peridot, wepppy2, wepppyo3, rosetta, weppcloud-wbt, markdown-doc, rq-dashboard
  - Installs `uv`, `rustup`, `npm` globals (`npx`, `@openai/codex`) unless `--skip-node`
  - Installs `wctl` via `wepppy/wctl/install.sh` if present
  - Touches static JS placeholders for live-reload expectations
  - Optional: copy an env file to `wepppy/docker/.env`
  - Optional: install and enable `cao-server.service`
- Flags
  - `--env-file <path>`: copy to `wepppy/docker/.env`
  - `--with-cao`: install/enable CAO systemd unit
  - `--skip-docker`: do not install Docker
  - `--skip-node`: skip npm/global tools
  - `--readonly-pattern <glob>`: mark matching run dirs with a `READONLY` file (utility)
- Idempotent behavior
  - Repos are pulled fast-forward when already cloned
  - User/group membership and dirs are checked before creating

Examples:

```bash
# Minimal
sudo bash services/cao/scripts/weppcloud_deploy.sh

# With CAO service and env file
sudo bash services/cao/scripts/weppcloud_deploy.sh --env-file ~/wepppy.env --with-cao

# Skip Docker (already installed) and Node tooling
sudo bash services/cao/scripts/weppcloud_deploy.sh --skip-docker --skip-node
```

## Script: ci_samurai_dryrun.sh

Purpose: Exercise the CI Samurai workflow across three hosts, collect artifacts, and publish to a timestamped folder under `/wc1` on nuc1.

- What it does
  - Triage on nuc1: `pytest` for NoDb and WEPP with short trace and maxfail limits
  - Extracts the first failing test and re-runs once to detect easy flakes
  - Validation on nuc2: clean workspace, run the first failing test (or a minimal subset)
  - Flake stress on nuc3: run the first failing test N times to profile intermittency
  - Publishes logs to `nuc1:/wc1/ci-samurai/logs/<timestamp>/`
- Flags
  - `--nuc1 <host>`: triage host (default `nuc1`)
  - `--nuc2 <host>`: validation host (default `nuc2`)
  - `--nuc3 <host>`: flake host (default `nuc3`)
  - `--repo <path>`: repo path on remotes (default `/workdir/wepppy`)
  - `--wc1 <path>`: wc root on nuc1 (default `/wc1`)
  - `--loops <n>`: flake loop count (default `10`)
  - `--nodb-only`: only run `tests/nodb`
  - `--wepp-only`: only run `tests/wepp`

Examples:

```bash
# Default hosts, both suites
bash services/cao/scripts/ci_samurai_dryrun.sh

# NoDb only, more flake loops
bash services/cao/scripts/ci_samurai_dryrun.sh --nodb-only --loops 20

# Custom hosts
bash services/cao/scripts/ci_samurai_dryrun.sh --nuc1 dev-a --nuc2 dev-b --nuc3 dev-c
```

## Notes & Troubleshooting

- Ensure each NUC has a checkout at `/workdir/wepppy` and Docker running (unless `--skip-docker`).
- If triage commands fail due to environment, check `docker/.env` on nuc2 and copy from nuc1 using the `--env-file` flag for the deploy script.
- DuckDNS updates are handled by pfSense; the scripts do not call DuckDNS endpoints.
- If `wctl` is not found after deploy, open a new shell or add it to your PATH per your host’s `wctl` installer output.
- For remote workers, ensure:
  - `/wc1` and `/geodata` are mounted on the worker hosts (NFS to forest1).
  - `RQ_REDIS_URL` reaches forest1’s Redis (port 6379 must be reachable from NUCs).
  - `docker/.env` exists on each host and `UID/GID` match forest1 to avoid permission drift.

## References

- CI Samurai design: services/cao/ci-samurai.md
- Agent prompt: services/cao/ci-samurai/agent-prompt.md
- Deploy script: services/cao/scripts/weppcloud_deploy.sh
- Dry-run: services/cao/scripts/ci_samurai_dryrun.sh
