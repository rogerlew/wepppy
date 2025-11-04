## **wctl (Typer CLI for WEPPcloud)**

### **Overview**

`wctl` is now a Typer-powered Python CLI that orchestrates the WEPPcloud Docker Compose stacks and the companion tooling that lives in `tools/wctl2`. The thin shell shim installed by `./wctl/install.sh` simply resolves the project root, pins the desired compose file, exports `PYTHONPATH`/`WCTL_COMPOSE_FILE`, and defers to `python -m wctl2`. Typer’s rich help/auto-completion replaces the legacy Bash wrapper and man page while keeping command names and behaviour familiar.

Key design points:
- A shared `CLIContext` (see `tools/wctl2/context.py`) merges `docker/.env`, optional host overrides (`WCTL_HOST_ENV`), and any shell-provided overrides into a temporary env file that every command reuses.
- All first-class helpers are implemented as Typer subcommands, so `wctl <command> --help` shows usage, defaults, and options without maintaining a separate manual page.
- Anything that is not recognised as a Typer subcommand is forwarded to `docker compose`, with support for common prefixes (`wctl docker compose ps`, `wctl compose up`, etc.) and INFO-level logging so you can see the exact call.

### **Quick Start**

```bash
cd /workdir/wepppy
./wctl/install.sh dev    # pin docker/docker-compose.dev.yml (default)
# or
./wctl/install.sh prod   # pin docker/docker-compose.prod.yml

# optional: install to a custom bin directory
WCTL_SYMLINK_PATH="$HOME/.local/bin/wctl" ./wctl/install.sh dev
```

After installation you can explore the CLI via:

```bash
wctl --help
wctl run-test-profile --help
wctl docker compose config --help
```

### **Available Commands**

All commands mirror the legacy behaviour, but now live under the Typer dispatcher:

- `wctl doc-lint` / `doc-catalog` / `doc-toc` / `doc-mv` / `doc-refs` / `doc-bench` – wrappers around the `markdown-doc` toolkit with argument parity.
- `wctl build-static-assets` – calls `wepppy/weppcloud/static-src/build-static-assets.sh`, adding `--prod` automatically when the installer targets the production compose file.
- `wctl restore-docker-data-permissions` – repairs ownership for `.docker-data/*` using the UID/GID from the active env file.
- `wctl run-npm` – runs host-side npm/Yarn scripts with `--prefix wepppy/weppcloud/static-src` (plain npm commands like `install`, `test`, `lint`, etc.).
- `wctl run-pytest` – executes pytest inside the running `weppcloud` container (`pytest tests` by default).
- `wctl run-stubtest` – runs stubtest from the container (default target `wepppy.nodb.core`).
- `wctl run-stubgen` – regenerates stubs (`python tools/sync_stubs.py`).
- `wctl check-test-stubs` / `check-test-isolation` – launch the diagnostic scripts inside the container.
- `wctl run-test-profile` / `run-fork-profile` / `run-archive-profile` – drive the profile playback FastAPI service, defaulting to the canonical `backed-globule` smoke profile when no overrides are supplied.

Every command supports `--help`, so discovery is as simple as `wctl run-pytest --help`.

### **Docker Compose Passthrough**

If Typer cannot match the first argument to a registered command, the shim trims optional `docker compose` prefixes and delegates to Docker Compose with the context-managed env file:

```bash
wctl ps
wctl compose ps
wctl docker compose logs weppcloud
```

Each passthrough call is logged (for example, `INFO:wctl2:docker compose ps`) so you can see the exact command that was executed.

### **Environment Handling**

- The generated temp env file always starts with `docker/.env` and merges an optional host override.
- Set `WCTL_HOST_ENV` (absolute or project-relative) to point at an additional `.env` file that should be layered on top.
- Any shell environment variables referenced in the active compose file act as the final overrides – for example export `POSTGRES_PASSWORD` before calling `wctl up`.
- `WCTL_COMPOSE_FILE` is exported by the shim so Typer can reuse the selected compose file without requiring extra flags on every invocation.

### **Testing & Tooling Workflow**

Use the Typer helpers instead of crafting long `docker compose exec` commands manually:

```bash
wctl run-pytest tests/weppcloud/routes/test_climate_bp.py
wctl run-pytest tests --maxfail=1
wctl run-stubtest wepppy.nodb.core
wctl check-test-stubs
wctl run-npm lint
```

Because the commands execute inside the running containers (or with the correct host prefix for npm), they reflect the same environment used in production deployments.

### **Host Environment Overrides**

When a project-root `.env` exists, the CLI automatically merges it on top of `docker/.env`. Relative paths provided via `WCTL_HOST_ENV` are resolved against the project directory by `CLIContext`. Temporary overrides can be added by exporting shell variables before running `wctl`.

### **Profile Playback Smokes**

The playback helpers stream directly from the `services/profile_playback` FastAPI service. Typical smokes look like:

```bash
wctl run-test-profile backed-globule --dry-run
wctl run-fork-profile backed-globule --timeout 120
wctl run-archive-profile backed-globule --archive-comment "smoke test" --timeout 120
```

All commands print the HTTP target and payload to stderr before streaming the service response.

> **Heads-up:** WEPPcloud sets authentication cookies as `Secure`, so playback can only perform automated logins against the public HTTPS host (for example `https://wc.bearhive.duckdns.org/weppcloud`). When pointing at the internal `http://weppcloud:8000/weppcloud` endpoint you must supply your own non-secure cookie via `--cookie`/`--cookie-file`, otherwise login fails.

### **Upgrading from the Legacy Bash Wrapper**

- The legacy script, manual page, and bespoke subcommand plumbing have been removed.
- Any existing symlinks pointing at the old `wctl.sh` should be refreshed by re-running `./wctl/install.sh <env>`.
- Documentation and help are now delivered directly by Typer (`wctl --help`), so no additional man page is required.

### **Troubleshooting**

- Ensure `python3` is available and matches the runtime used inside the Docker images (3.11+).
- If Python cannot locate the Typer package, confirm the shim was installed via `./wctl/install.sh` so that `PYTHONPATH` includes both the repository root and `tools/`.
- For compose passthrough issues, re-run with `wctl --log-level DEBUG docker compose …` to surface more detail (Typer accepts the global `--log-level` option before the command name).

### **Next Steps**

- Integrate the new CLI into CI pipelines (`wctl run-pytest`, `wctl docker compose config --quiet`, etc.).
- Remove any downstream references to the legacy `profile_playback_cli.py` helpers; the Typer commands are the new canonical interface.
- Keep an eye on `tools/wctl2/SPEC.md` for additional enhancements (command grouping, completion scripts, richer logging).
