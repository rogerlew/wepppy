# Browse Microservice

> **See also:** [AGENTS.md](../../AGENTS.md) for Flask web application and microservices architecture.

## Why this exists
- This service offloads all filesystem browsing and metadata endpoints from the Flask monolith onto a Starlette app that can be scaled and rate-limited independently.
- It protects the main site from aggressive crawlers that were hammering directory listings while keeping the familiar `/browse`, `/download`, and `gdalinfo` features intact.
- The microservice runs under gunicorn with uvicorn workers (port 9009 in production) and is fronted by HAProxy.

## High-level architecture
- **Application**: `wepppy/microservices/browse.py`
  - Creates a Starlette app and registers the browse UI plus the download and gdalinfo helper routes.
  - Reuses the existing Jinja templates (directory listings, text viewer, etc.) but renders them outside Flask.
  - Contains shims so templates that call `url_for(...)` or expect `SITE_PREFIX` still work.
- **Async execution**
  - Directory listings (`ls -l`, `wc -l`) run via `asyncio.create_subprocess_shell` and `asyncio.gather` instead of blocking subprocess calls.
  - Pandas I/O (`read_csv`, `read_parquet`) and heavy file reads are moved into `asyncio.to_thread` keeps the event loop responsive.
- **Supporting modules**
  - `_download.py`: serves file downloads, parquet→CSV conversion, and aria2c manifests.
  - `_gdalinfo.py`: shells out to `gdalinfo -json` and returns raster metadata.

## Directory layout (key files)
```
wepppy/microservices/
  browse.py              # Starlette application factory and browse UI logic
  _download.py           # Download + aria2c routes shared with browse
  _gdalinfo.py           # gdalinfo JSON route shared with browse
  _service_files/        # systemd / gunicorn configs (browse service runs on 9009)
```  
Templates remain in `wepppy/weppcloud/routes/browse/templates/browse/`.

## Routes & options
| Route | What it does | Notable query params |
|-------|---------------|----------------------|
| `/weppcloud/runs/{runid}/{config}/browse/` | Top-level directory view with pagination and filters. | `page` (1-based start index), shell-style wildcard filter (`../output/p1.*`), `diff={runid}` to show diff links against another run. |
| `/weppcloud/runs/{runid}/{config}/browse/{subpath}` | Lists a directory or displays a file. Handles text, archives, tables (pandas), and binary downloads. | Same as above plus file-specific options: `repr=1` (management/soil annotation), `raw=1`, `download=1`. Parquet/CSV viewers expose convenience links (pivot, CSV). |
| `/weppcloud/runs/{runid}/{config}/download/{subpath}` | Direct file download. Converts parquet to CSV when `?as_csv=1`. | `as_csv=1` for parquet conversion. |
| `/weppcloud/runs/{runid}/{config}/aria2c.spec` | Generates an aria2c manifest for pulling the entire run. | *(no additional options)* |
| `/weppcloud/runs/{runid}/{config}/gdalinfo/{subpath}` | Returns `gdalinfo -json` for a raster file. | *(no additional options)* |

All routes honor the site prefix automatically (default `/weppcloud`). If the service is deployed behind another prefix, set `SITE_PREFIX` in the environment.

## Behavior details
- **Security**
  - Path traversal is blocked by comparing real paths against the resolved run directory.
  - Missing resources return 404/JSON errors rather than Flask responses.
- **Performance**
  - Async subprocesses mean directory listings are ~4–10× faster for most runs.
  - Large file conversions run in thread executors; gunicorn workers stay responsive.
- **Template shims**
  - `url_for` supports the common `command_bar.static` and `static` endpoints. Extend the shim before pulling additional Flask templates.
- **Logging**
  - `/health` polling is filtered from gunicorn/uvicorn access logs.

## Manifest-backed directory listings
- `manifest.db` is created when a project flips to readonly; it lives at the run root and is built by `create_manifest` in `browse.py` using the same traversal logic as on-demand browsing.
- SQLite stays in WAL mode with `synchronous=NORMAL` for fast reads. The `entries` table stores `dir_path`, `name`, `entry_type` (file, directory, symlink), `size_bytes`, `mtime_ns`, `child_count`, and `symlink_target`. `entry_type` sorts with raw byte ordering so listings match `ls`.
- Directory rows carry a `child_count` so pagination never shells out. Symlink rows capture `symlink_is_dir` so the UI can label folder links correctly and suppress download buttons for directory links.
- `browse_response` tags responses that came from the manifest so breadcrumbs can show a subtle badge (for example “manifest cached”).
- Queries fall back to on-demand scans whenever the manifest is missing, unreadable, or a pattern cannot be expressed with SQLite `GLOB` semantics.

### Creation workflow
- `project_rq.set_run_readonly_rq(runid, readonly)` performs the toggle: it updates the `READONLY` sentinel, removes any stale manifest, and rebuilds `manifest.db` for non-child runs.
- The worker publishes start/complete/error messages through `StatusMessenger` so `Project._notifyCommandBar` can report progress without changing the browser contract.
- The project blueprint queues `set_run_readonly_rq`; the worker flips the `READONLY` sentinel and handles manifest creation/removal before reporting back to the UI.
- Clearing readonly removes `manifest.db` (if present) after the sentinel file disappears.

### Browse integration
- `get_page_entries` checks for `manifest.db` first and serves listings directly from SQLite. Only when the manifest is absent does it shell out to `ls`/`wc`.
- Directory rows use the stored `child_count` and symlink metadata so nested counts are instantaneous and links render correctly.
- Symlink directories inherit the folder styling and omit download links; file symlinks still show download buttons and targets (`name -> dest`).
- Breadcrumbs and JSON payloads surface a `using_manifest` flag for observability and to aid debugging.

### Known limitations
- The manifest only refreshes when readonly changes; manual edits to a readonly tree are not detected until a rebuild runs.

## Operating the service
- Systemd unit: `wepppy/microservices/_service_files/gunicorn-browse.service` (binds to 0.0.0.0:9009 with uvicorn workers).
- Health check: `GET /health` returns `OK` — HAProxy uses this for backend status.
- Restart after code changes: `systemctl restart gunicorn-browse` (or equivalent in your environment).

## Future enhancements
- Expand the `url_for` shim (or replace it) before migrating more Flask templates.
- Consider caching popular directory listings or large file renders once LRU caching is revisited.
- Centralize run-context resolution so `_download.py`, `_gdalinfo.py`, and future helpers reuse a single implementation.
