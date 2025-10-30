## **wctl (weppcloud control)**

### **Overview**

wctl is a command-line wrapper script designed to simplify the management of the wepppy Docker Compose development environment.  
The primary purpose of this tool is to provide a global command that executes docker compose with the project-specific configuration files, regardless of the user's current working directory. It eliminates the need to repeatedly cd into the project folder (/workdir/wepppy) and type the full docker compose command with its environment and file flags.

### **How It Works**

The wctl script is a simple yet powerful Bash script that performs the following actions in sequence:

1. **Sets Project Directory:** The script derives the project root dynamically based on the location of the wctl directory.  
2. **Changes Directory:** It immediately changes its execution context to that project directory so that all relative paths within the compose file resolve correctly.  
3. **Executes Docker Compose:** It runs docker compose using a generated env file that starts with `docker/.env` and, if present, merges in overrides from the project root `.env` (or the path supplied via `WCTL_HOST_ENV`). The compose file selected during installation (dev or prod) is used for all commands.  
4. **Forwards Arguments:** Any arguments or commands you pass to wctl (e.g., up \-d, down, logs) are appended to the end of the docker compose command using the $@ shell parameter.

This allows a command like wctl ps to be translated seamlessly into:

```Bash
# (executed from within the /workdir/wepppy directory)  
docker compose \--env-file docker/.env \-f docker/docker-compose.dev.yml ps
```

### **Built-in Helpers**

- `wctl doc-lint`: wraps `markdown-doc lint`. With no arguments it runs `markdown-doc lint --staged --format json`, prints a short notice to stderr, and streams the JSON result so tooling can parse it. Pass any arguments to override the defaults (for example `wctl doc-lint --path docs --format sarif`).
- `wctl doc-catalog`: forwards directly to `markdown-doc catalog`. Use flags like `--path docs --format json` to regenerate scoped catalogs without touching restricted directories.
- `wctl doc-toc`: accepts positional Markdown paths (converted to `--path` under the hood) plus the native flags such as `--update` or `--diff`. Requires at least one target so accidental repo-wide sweeps are avoided.
- `wctl doc-mv`: performs a dry-run via `markdown-doc mv --dry-run …`, then prompts on `/dev/tty` before applying changes. Use `--dry-run-only` to skip the apply step or `--force` to bypass the confirmation prompt.
- `wctl doc-refs`: wraps `markdown-doc refs` for locating inbound links or anchors ahead of refactors. Combine with `--path` to constrain the search space when large directories exist.
- `wctl doc-bench`: proxies `markdown-doc-bench` so you can benchmark documentation operations (`--warmup`, `--iterations`, `--path`) from the same CLI.
- `wctl build-static-assets`: runs the frontend build script (`static-src/build-static-assets.sh`) with the correct Compose profile baked into the arguments.
- `sudo wctl restore-docker-data-permissions`: resets ownership and permissions for the directories under `.docker-data/`. Postgres data and backup paths are restored to `postgres:postgres` (UID/GID `999`), Redis gets `redis:redis` (also `999`), and the application log directory (`.docker-data/weppcloud/`) is aligned with the UID/GID specified in `docker/.env` (defaults to `1000:993`). Use this whenever an accidental `chown` prevents the containers from writing to their bind mounts.
- `wctl flask-db-upgrade`: executes `flask --app wepppy.weppcloud.app db upgrade` inside the running `weppcloud` container. Any additional arguments are forwarded, so `wctl flask-db-upgrade --tag current` works the same as the underlying Flask-Migrate command.
- `wctl man` (or `man wctl` after installation): displays the wctl manual page. Additional arguments are passed through to `man`, so `wctl man --no-pager` works as expected.
- `wctl update-stub-requirements`: runs `tools/update_stub_requirements.py` to analyse mypy output and refresh `docker/requirements-stubs-uv.txt`. Pass any script flags (for example `--no-verify`) after the command.
- `wctl run-pytest`: executes `pytest` inside the `weppcloud` container (defaults to `pytest tests`). Pass extra arguments to forward them to pytest; for example, `wctl run-pytest tests/weppcloud/routes/test_climate_bp.py`.
- `wctl run-stubtest`: runs `stubtest` inside the container with the appropriate environment (defaults to `wepppy.nodb.core`). Provide module names to narrow the check.
- `wctl run-npm`: runs `npm` on the host with `--prefix wepppy/weppcloud/static-src`. Example: `wctl run-npm lint`, `wctl run-npm test`, or `wctl run-npm check`.
- `wctl run-stubgen`: regenerates the local `stubs/` tree via `python tools/sync_stubs.py`.
- `wctl check-test-stubs`: executes `python tools/check_stubs.py` inside the container to ensure sys.modules stubs match their public APIs.
- `wctl check-test-isolation`: launches `python tools/check_test_isolation.py` inside the container. Supports all script flags (`--quick`, `--strict`, `--iterations`, `--json`, etc.) and surfaces order-dependent failures plus leaked global state before they surprise downstream suites.
- `wctl run-status-tests`: compiles and runs the Go unit/integration tests for `services/status2` using the compose-managed `status-build` helper (golang:1.25-alpine). The helper runs `go mod tidy` before `go test`; extra arguments after the command are forwarded to `go test`.
- `wctl run-preflight-tests`: same workflow as above but scoped to `services/preflight2`. Use flags like `-tags=integration ./internal/server` to exercise the Redis/WebSocket harness.

### **Host Environment Overrides**

If a `.env` file exists at the project root, wctl automatically merges it on top of the required `docker/.env` when generating the temporary environment passed to docker compose. Keys defined in the host file override the defaults from `docker/.env`, making it easy to keep machine-specific values out of version control.  
Set the `WCTL_HOST_ENV` environment variable (absolute or project-relative path) before invoking wctl if you need to use a different host-side env file.

After the files are merged, wctl scans the active docker compose file for `${VAR}` placeholders and, when a matching variable is defined in the current shell environment, copies that value into the generated env file as the final override. This lets you keep secrets in exported environment variables (or injected by tools like `direnv`) without committing them anywhere.

### **pytest Workflow**

- Keep `docker/.env` populated with the stack-wide defaults (UID/GID, secrets, hostnames). Wctl always starts there so the containers boot with predictable values.
- Add a project-root `.env` (gitignored) or point `WCTL_HOST_ENV` at a private file for local overrides such as API keys, database URLs, and filesystem mount points.
- For temporary values (CI, ad-hoc debugging), simply export environment variables before running `wctl`; the wrapper pulls them into the generated env file automatically.
- Run targeted suites aggressively:
  ```bash
  wctl run-pytest tests/weppcloud/routes/test_climate_bp.py
  wctl run-pytest tests/weppcloud/routes  # package-level smoke
  wctl run-pytest tests --maxfail=1        # full run before handoff
  ```
- Make `wctl run-pytest …` part of your default workflow anytime routes, controllers, or shared utilities change. The command exercises the code inside the real container image, so failures mirror production.

### **Running Type Checks / Stubtest**

Because the development Docker image installs the stub wheels listed in `docker/requirements-stubs-uv.txt`, run static checks inside the container so the environment matches production. The helpers above take care of the `/tmp` working directory, `PYTHONPATH`, and cache location for you:

```bash
wctl run-pytest                      # pytest tests
wctl run-stubtest wepppy.nodb.core   # stubtest target
wctl run-stubgen                     # rebuild stubs/wepppy/
```

Use `wctl update-stub-requirements` before rebuilding the image when new dependencies require additional stub packages.

### **Installation**

1. **Configure the target compose file.**  
   Run the installer (located in the wctl directory) from the project root to select the compose file that wctl should use.  
   Ensure `python3` is on your PATH before running these commands.
   ```Bash
   cd /workdir/wepppy
   ./wctl/install.sh dev    # use docker/docker-compose.dev.yml
   ./wctl/install.sh prod   # use docker/docker-compose.prod.yml
   ```
   You can re-run the installer at any time to switch environments.

2. **(Optional) Adjust the symlink location.**  
   The installer ensures a symlink exists at `/usr/local/bin/wctl` (or at the path specified by the `WCTL_SYMLINK_PATH` environment variable).  
   If the default location requires elevated privileges, re-run the installer with `sudo` or choose a writable directory:
   ```Bash
   WCTL_SYMLINK_PATH="$HOME/.local/bin/wctl" ./wctl/install.sh dev
   ```
   Verify the installation with `which wctl`; it should resolve to your chosen path.

   The installer also attempts to place the manual page at `/usr/local/share/man/man1/wctl.1`. If you lack permissions there, rerun with `sudo` or set `WCTL_MAN_PATH` to a writable location (for example `"$HOME/.local/share/man/man1/wctl.1"`), then refresh your `MANPATH`.
