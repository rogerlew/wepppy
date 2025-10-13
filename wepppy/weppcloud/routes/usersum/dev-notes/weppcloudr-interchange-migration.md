# WEPPcloudR Pipeline Migration

Notes for moving the WEPPcloudR blueprint and Chinmay’s `new_report.Rmd`
off the legacy Arc export stack and onto the interchange/query-engine
assets. Captures the technical debt we need to unwind and the platform
choices for running R workloads.

---

## Current State (2025-03)

- Routes in `weppcloudr.py` shell out to R/Rmd scripts located under
  `/workdir/WEPPcloudR/scripts`. Those scripts expect Arc-produced
  artifacts (`export/arcmap/subcatchments.WGS.json`,
  `export/totalwatsed*.csv`, etc.).
- `deval_details` still calls `wepppy.export.arc_export`, which requires
  an ArcGIS runtime even when the interchange parquet files already
  exist.
- The cache key for rendered reports hashes `export/totalwatsed2.csv`;
  if interchange data changes, the hash does not update.
- Bare `except:` blocks swallow tracebacks and we ignore `Popen`
  exit codes, so R failures quietly produce empty HTML.
- R scripts fall back to HTTP GETs against `https://wepp.cloud/...`
  whenever local CSVs are missing, which breaks offline usage and
  produces subtle mismatches when the remote run diverges from the
  filesystem.

---

## Migration Targets

1. **Bootstrap with interchange**
   - Call `activate_query_engine(wd, run_interchange=True)` (or a thin
     wrapper) before invoking any R scripts.
   - Switch the cache key to `wepp/output/interchange/totalwatsed3.parquet`
     (or whatever parquet feeds the report) instead of CSVs.

2. **R data dependencies**
   - Replace CSV/JSON readers with parquet queries:
     - `totalwatsed3.parquet` (daily watershed balance).
     - `chanwb.parquet` (channel water balance).
     - `ebe_pw0.parquet` (event-based outputs).
     - `loss_pw0.*.parquet`, `watershed/hillslopes.parquet`,
       `landuse/landuse.parquet`, `soils/soils.parquet` for attribute
       enrichment.
   - `read_subcatchments()` should pull geometry from
     `watershed/subcatchments*.json` or `watershed/hillslopes.parquet`
     rather than Arc exports, with the old paths retained only as a
     final fallback.
   - Add DuckDB/Arrow accessors on the R side so we can query parquet
     directly instead of materialising large tables via `data.table`.

3. **Route hardening**
   - Check `Popen.returncode` and bubble errors through
     `exception_factory`.
   - Emit structured log lines when the R invocation fails (stdout,
     stderr, command).
   - Drop the `global` on `WEPPCLOUDR_DIR` and move these roots into
     configurable settings.

4. **Testing + validation**
   - Add unit coverage for cache-key selection and the interchange
     bootstrap helper.
   - Provide an integration smoke test that renders `new_report.Rmd`
     against a fixture run directory with parquet assets only (no Arc
     exports present).

---

## R Runtime Strategy

- **Dedicated container**: keep R (Rscript, rmarkdown, Shiny) isolated
  from the Flask/WEPP Python image.
  - Base on `rocker/r-ver` (Debian + pre-compiled R) to avoid long build
    times; layer R package installs with `renv` or `pak` to parallelise
    compilation.
  - Share the WEPP run workspace via a bind mount or Docker volume so
    the R container can read interchange parquet files.
  - Provide an entrypoint that runs `Rscript` with a manifest describing
    which report to render and where to drop output HTML.

- **Execution patterns**
  - **Sync render**: Flask route shells out to `docker run --rm
    weppcloud-r report ...` and streams stdout/stderr for diagnostics.
  - **Async render**: push a job to the task queue (e.g. RQ/Celery);
    worker invokes the R container and stores results in the export dir.

- **Shiny support**
  - Build the same base image with Shiny Server (or `shinyproxy`) so we
    can host interactive dashboards. Individual apps can live under
    `/srv/shiny-server/<app>`; multi-tenancy is fine as long as resource
    limits are enforced (cgroup quotas).
  - For heavier workloads or untrusted code, provisioning per-app
    containers is safer, but start with a shared Shiny Server pod to
    simplify routing.

- **Inter-container calls**
  - Worst-case, Flask writes a render request (JSON) to disk or Redis,
    and the R container polls for work. Prefer gRPC/HTTP between
    containers when we need richer status reporting.

---

## Open Questions / Follow-ups

- How do we want to manage R package versions? (`renv` lockfile vs
  manual `pak::pkg_install` script.)
- Should rendered HTML stay on disk or move to object storage (S3,
  MinIO) for distribution?
- Do we retire the old viz scripts under `/workdir/viz-weppcloud`, or
  maintain parity until R-side parity is achieved?
- Define monitoring: where do R render logs go and how do we surface
  failures back to the UI?

---

## Deval Details Service Plan

- Introduce an `ensure_interchange(ctx)` helper that wraps
  `activate_query_engine(str(ctx.active_root), run_interchange=True)`
  so parquet assets are present before delegating to the R renderer.
  Any activation failure should bubble up via `exception_factory`.
- `/runs/<runid>/<config>/report/deval_details` now calls the
  `weppcloudr` container via HTTP (no user-facing redirect). The Flask
  view streams the HTML returned by the service and forwards relevant
  headers while logging non-200 statuses.
- Query parameters such as `pup` are passed through so the container can
  resolve `_pups` directories safely.
- When JWT support lands, forward the bearer token to the R service and
  validate it there.

---

## R Service Container (`weppcloudR/`)

1. **Dockerfile scaffold**
   - Base: `rocker/r-ver:4.3.2` (minimal Debian + R).
   - Install `pak` and resolve runtime deps (`rmarkdown`, `plumber`,
     `duckdb`, `arrow`, `jsonlite`, `glue`, `logger`, `stringr`,
     `lubridate`, `dplyr`).
   - Copy service sources into `/srv/weppcloudr` and set working dir.
   - Default entrypoint: `Rscript docker-entrypoint.R` (starts Plumber).
2. **Runtime layout**
   - `docker-entrypoint.R`: configure logging, read env (`PORT`,
      mount roots `/geodata`, `/wc1`), mount Plumber router (`plumber.R`).
   - `plumber.R`: expose `GET /healthz` plus `GET /runs/<run>/<cfg>/report/deval_details`
     which calls an R wrapper around `rmarkdown::render`.
   - Accept run directory via bind mounts (`/geodata`, `/wc1`); expect
     interchange assets under `<root>/<runid>/wepp/output/interchange`.
   - Write rendered HTML to stdout response; optionally persist to
     `/data/<runid>/export/WEPPcloudR`.
3. **Networking and proxy**
   - Container listens on `${PORT:-8050}`; Caddy routes `/weppcloudr/*`
     to that port.
   - Support `X-Forwarded-*` headers for logging, and leave hooks for
     future JWT validation.
4. **Developer helpers**
   - Add README with build/run instructions, including `docker build -t
     weppcloudr-service .` and example `docker run` with bind mounts.
   - Later: Makefile targets + CI job to build/push the image.

Open tasks for the container:

- Decide on package pinning method (`pak::snapshot()` vs `renv`).
- Provide sample interchange dataset + automated smoke test that hits
  `/render/deval` and asserts a non-empty HTML payload.
- Mirror the repo layout inside the container (bind `/geodata`,
  `/wc1`, and the legacy `WEPPcloudR` scripts) so the renderer can use
  existing R Markdown templates during the transition.

---

## Current progress (2025-10-13)

- `deval_details` route now ensures interchange assets and proxies the
  rendered HTML from the `weppcloudr` service, preserving query string
  parameters (e.g. `pup`).
- Plumber service writes render logs with call stacks (`sys.calls()`)
  and now reports concise error messages. Dockerfile updated to install
  `arrow` so parquet reads succeed.
- R helpers refactored to consume interchange data:
  * `read_subcatchments()` now reads WBT GeoJSON and joins
    `hillslopes.parquet`, `landuse.parquet`, and `soils.parquet` to
    produce enriched attributes (`area_ha`, `landuse`, `soil`, `Texture`,
    `gradient`, `wepp_id`).
  * `process_totalwatsed()`, `process_chanwb()`, and `process_ebe()` now
    read from `totalwatsed3.parquet`, `chanwb.parquet`, and
    `ebe_pw0.parquet`.
  * Climate summary derives from parquet aggregates instead of scraping
    `loss_pw0.txt`.
- Outstanding work:
  * Rebuild the container (with the new `arrow` dep) and rerun the
    report—currently failing due to the bare GeoJSON missing `soil`,
    `landuse`, etc. Verify the enriched joins produce the expected
    columns for all runs.
  * Update downstream helpers (`merge_daily_Vars`, cumulative charts) to
    align with canonical column names (`Runoff`, `Lateral Flow`,
    `Streamflow`, etc.).
  * Remove remaining HTTP/Arc fallback code once the parquet pipeline is
    validated.
  * Add a smoke test that mounts a sample run directory and hits the
    `/runs/.../report/deval_details` endpoint.
