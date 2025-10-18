## **wctl (weppcloud control)**

### **Overview**

wctl is a command-line wrapper script designed to simplify the management of the wepppy Docker Compose development environment.  
The primary purpose of this tool is to provide a global command that executes docker compose with the project-specific configuration files, regardless of the user's current working directory. It eliminates the need to repeatedly cd into the project folder (/workdir/wepppy) and type the full docker compose command with its environment and file flags.

### **How It Works**

The wctl script is a simple yet powerful Bash script that performs the following actions in sequence:

1. **Sets Project Directory:** The script derives the project root dynamically based on the location of the wctl directory.  
2. **Changes Directory:** It immediately changes its execution context to that project directory so that all relative paths within the compose file resolve correctly.  
3. **Executes Docker Compose:** It runs docker compose, pointing to the shared env file (docker/.env) and the compose file selected during installation (dev or prod).  
4. **Forwards Arguments:** Any arguments or commands you pass to wctl (e.g., up \-d, down, logs) are appended to the end of the docker compose command using the $@ shell parameter.

This allows a command like wctl ps to be translated seamlessly into:

```Bash
# (executed from within the /workdir/wepppy directory)  
docker compose \--env-file docker/.env \-f docker/docker-compose.dev.yml ps
```

### **Built-in Helpers**

- `wctl build-static-assets`: runs the frontend build script (`static-src/build-static-assets.sh`) with the correct Compose profile baked into the arguments.
- `sudo wctl restore-docker-data-permissions`: resets ownership and permissions for the directories under `.docker-data/`. Postgres data and backup paths are restored to `postgres:postgres` (UID/GID `999`), Redis gets `redis:redis` (also `999`), and the application log directory (`.docker-data/weppcloud/`) is aligned with the UID/GID specified in `docker/.env` (defaults to `33:993`). Use this whenever an accidental `chown` prevents the containers from writing to their bind mounts.
- `wctl flask-db-upgrade`: executes `flask --app wepppy.weppcloud.app db upgrade` inside the running `weppcloud` container. Any additional arguments are forwarded, so `wctl flask-db-upgrade --tag current` works the same as the underlying Flask-Migrate command.
- `wctl man` (or `man wctl` after installation): displays the wctl manual page. Additional arguments are passed through to `man`, so `wctl man --no-pager` works as expected.
- `wctl update-stub-requirements`: runs `tools/update_stub_requirements.py` to analyse mypy output and refresh `docker/requirements-stubs-uv.txt`. Pass any script flags (for example `--no-verify`) after the command.

### **Running Type Checks / Stubtest**

Because the development Docker image installs the stub wheels listed in `docker/requirements-stubs-uv.txt`, run static checks inside the container so the environment matches production. The bind-mounted workspace is read-only for the container user, so run checks from `/tmp`, add the project to `PYTHONPATH`, and redirect mypy’s cache to `/tmp`:

```bash
wctl exec weppcloud bash -lc \
  "cd /tmp && PYTHONPATH=/workdir/wepppy MYPY_CACHE_DIR=/tmp/mypy_cache /opt/venv/bin/mypy -m wepppy.nodb.core"
wctl exec weppcloud bash -lc \
  "cd /tmp && PYTHONPATH=/workdir/wepppy MYPY_CACHE_DIR=/tmp/mypy_cache /opt/venv/bin/stubtest wepppy.nodb.core.wepp"
```

Sync the standalone stub tree and `py.typed` marker with:

```bash
python tools/sync_stubs.py
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
