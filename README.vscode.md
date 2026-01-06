# VS Code Host Setup
> Local host + `.venv` configuration for VS Code/Pylance when you are not using the container.

## Overview
- Uses `uv` to manage the workspace `.venv` and match container requirements.
- Loads local stubs from `stubs/` for Pylance type info.
- Keeps runtime/test flows in Docker (`wctl`) for parity with production.

## Quick Start
1. Confirm GDAL 3.11.4 from ubuntugis-unstable:
   ```bash
   which gdal-config
   gdal-config --version
   ```
2. Create or refresh the venv:
   ```bash
   uv venv -p 3.12 .venv
   ```
3. Install dependencies with the host override:
   ```bash
   GDAL_CONFIG=/usr/bin/gdal-config \
   LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
   PATH=/usr/bin:$PATH \
   uv pip install -p .venv/bin/python \
     -r docker/requirements-uv.txt \
     -r docker/requirements-stubs-uv.txt \
     --overrides docker/requirements-uv-host-overrides.txt
   ```
4. VS Code should auto-detect `.venv` via `.vscode/settings.json`.

## VS Code Environment File
`.vscode/.env` is ignored by git. If you need to set GDAL paths for debug runs, use:
```bash
GDAL_CONFIG=/usr/bin/gdal-config
LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu
```

## Troubleshooting
- If you still see `libgdal 3.10.1` during installs, you likely have an older
  `/usr/local` GDAL shadowing apt:
  - Quick fix: keep the `GDAL_CONFIG`, `PATH`, and `LD_LIBRARY_PATH` overrides
    for `uv pip install`.
  - Clean fix: move `/usr/local/bin/gdal-config` and `/usr/local/lib/libgdal*`
    out of the way, then run `sudo ldconfig`.

## Notes
- Container pins stay in `docker/requirements-uv.txt`.
- Host-only overrides live in `docker/requirements-uv-host-overrides.txt`.
