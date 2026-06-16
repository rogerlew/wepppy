# Eliminate Arrow-to-Pandas Conversion from Browse

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`. It is self-contained so a future contributor can implement the package from this file and the repository tree alone.

## Purpose / Big Picture

WEPPcloud users browse run directories, preview parquet outputs, download filtered parquet files, export CSV, and launch D-Tale from the `browse` service. Today some of those paths convert Arrow or parquet data into pandas DataFrames inside long-lived Gunicorn workers. A production incident on June 16, 2026 showed `browse` workers retaining tens of GiB of RSS, and upstream PyArrow/pandas reports show that Arrow-to-pandas conversion can leave high process RSS even after Python objects are deleted.

After this change, a user should see the same browse behavior, but `browse` workers should inspect and export parquet data through bounded Arrow/DuckDB operations instead of pandas DataFrame materialization. The work is successful when route tests still pass, code search shows no Arrow-to-pandas conversion under `wepppy/microservices/browse`, and a representative parquet request does not leave a worker with high retained RSS after a settling window.

## Progress

- [x] (2026-06-16 18:58 UTC) Work-package scaffold and initial ExecPlan created.
- [x] (2026-06-16 19:10 UTC) Inventory exact browse call sites that materialize pandas DataFrames.
- [x] (2026-06-16 19:10 UTC) Define replacement helper interfaces and route-level behavior parity tests.
- [x] (2026-06-16 19:10 UTC) Replace parquet preview path.
- [x] (2026-06-16 19:10 UTC) Replace parquet-to-CSV export path.
- [x] (2026-06-16 19:10 UTC) Replace or isolate D-Tale handoff path.
- [x] (2026-06-16 19:10 UTC) Add observability helpers and request-path RSS logging.
- [x] (2026-06-16 19:24 UTC) Capture production-like local memory validation evidence.
- [x] (2026-06-16 19:24 UTC) Complete security review and package implementation closeout.

## Surprises & Discoveries

- Observation: Initial repository search before scaffold found browse-specific pandas materialization in `wepppy/microservices/browse/_download.py` and `wepppy/microservices/browse/flow.py`.
  Evidence: `rg -n "read_parquet|to_pandas|pyarrow|pandas\\.read" wepppy/microservices ...` reported `table.to_pandas()` in `_download.py` and `env.pd.read_parquet` in `flow.py`.

- Observation: The D-Tale browse bridge does not convert parquet to pandas; it forwards path and filter metadata to the separate D-Tale service.
  Evidence: `wepppy/microservices/browse/dtale.py` builds a JSON payload with `runid`, `config`, `path`, and optional `pqf`, then posts it to `/internal/load`.

- Observation: Unfiltered parquet previews previously had no explicit row cap because pandas read the whole file before rendering. The no-DataFrame path needs a cap to avoid large HTML and memory pressure.
  Evidence: `flow.py` now uses `BROWSE_PARQUET_PREVIEW_LIMIT` for filtered and unfiltered parquet previews.

- Observation: The first worker-level probe did not show the new INFO telemetry because the browse module loggers inherited a WARNING effective level.
  Evidence: After setting the changed browse loggers to INFO and restarting local `browse`, `docker compose logs` showed `browse parquet operation=preview` and `browse parquet operation=csv_export` entries with duration and RSS fields.

## Decision Log

- Decision: The implementation target is to eliminate pandas conversion from long-lived `browse` workers, not to rely on allocator cleanup knobs.
  Rationale: Arrow documents memory-pool release as best effort, and upstream issues show RSS can stay high after pandas/PyArrow conversion.
  Date/Author: 2026-06-16 18:58 UTC / Codex.

- Decision: Treat D-Tale as a discovery item.
  Rationale: D-Tale may require pandas internally. The package can still succeed by ensuring `browse` does not perform the conversion, but a D-Tale-specific replacement or disposable process may be follow-up scope.
  Date/Author: 2026-06-16 18:58 UTC / Codex.

- Decision: Cap unfiltered parquet previews with `BROWSE_PARQUET_PREVIEW_LIMIT`.
  Rationale: Preserving full-file HTML rendering would keep the dangerous memory profile for large parquet artifacts. A bounded preview preserves quick-look behavior while making the route safe for long-lived workers.
  Date/Author: 2026-06-16 19:10 UTC / Codex.

- Decision: Keep pandas in `browse` only for non-parquet CSV/TSV/pickle preview paths.
  Rationale: The package target is Arrow-to-pandas/parquet conversion. Removing unrelated pandas preview paths would widen scope and risk behavior drift.
  Date/Author: 2026-06-16 19:10 UTC / Codex.

## Outcomes & Retrospective

The package implementation is complete locally. Browse parquet preview and CSV export now use Arrow/DuckDB helpers instead of pandas DataFrames, D-Tale browse handoff remains a metadata-forwarding bridge, request-path RSS telemetry is visible in local container logs, and the focused plus broad microservice tests pass. Local Gunicorn validation against a 34 MB parquet artifact produced a 153 MB CSV response without reproducing the tens-of-GiB RSS failure signature. Remaining operational work is post-deployment observation on `wepp1` during the package's 14-day monitoring window.

## Context and Orientation

The `browse` service is a Starlette/FastAPI-style microservice served by Gunicorn with Uvicorn workers on port `9009`. Caddy proxies WEPPcloud run-directory browse and download URLs to this service. In production, the service reads run files from `/wc1/runs/...` inside the container, backed by `/geodata/wc1/runs/...` on the host.

Parquet is a columnar file format used for many WEPPcloud tabular artifacts. PyArrow can read parquet files into Arrow tables. pandas can convert those Arrow tables into DataFrames. A DataFrame is pandas' in-memory table structure. This package avoids converting parquet data into DataFrames inside `browse` because long-lived workers can retain high RSS after those conversions.

The relevant files are:

- `wepppy/microservices/browse/flow.py`, which renders directory listings and file previews.
- `wepppy/microservices/browse/_download.py`, which handles file downloads and parquet-to-CSV conversion.
- `wepppy/microservices/browse/browse.py`, which wires routes and templates.
- `wepppy/microservices/browse/dtale.py`, which launches or links D-Tale from browse.
- `wepppy/microservices/parquet_filters.py`, which already contains shared parquet filter logic from an earlier package.
- `docs/schemas/weppcloud-browse-parquet-filter-contract.md`, which defines existing filter semantics that must be preserved.
- `tests/microservices/test_browse_routes.py`, `tests/microservices/test_download.py`, and `tests/microservices/test_browse_dtale.py`, which are the route-level tests to extend.

This package is a faithful migration. "Faithful" means the visible behavior stays the same unless a change is explicitly documented and tested. "Wired" means the production route handlers use the new helpers; helper-only implementation is not enough.

## Plan of Work

First, inventory the current call sites. From `/home/workdir/wepppy`, search only the browse service with:

    rg -n "to_pandas|read_parquet|pd\\.|pandas" wepppy/microservices/browse tests/microservices

Record each relevant call site in `docs/work-packages/20260616_browse_arrow_pandas_elimination/tracker.md` and update this `Progress` section. Do not edit code until the inventory distinguishes production browse request paths from tests or harmless imports.

Second, create route-level tests that lock in behavior. The tests should cover at least unfiltered parquet preview, filtered parquet preview, unfiltered CSV export, filtered CSV export, parquet download, filtered parquet download, and D-Tale launch. If existing tests already cover a behavior, update them to assert the route output still matches after the implementation. Add a code-search style test or tooling check only if it can be kept robust; otherwise, document the `rg` gate in the verification checklist.

Third, define no-DataFrame parquet helpers. Prefer existing DuckDB or PyArrow APIs already present in the runtime image. Use DuckDB for SQL projection/filter/query work when it preserves the existing filter contract. Use PyArrow `ParquetFile.iter_batches` or equivalent batch APIs for CSV streaming when route behavior requires ordered full export. Keep helpers small and explicit. They should accept a filesystem path already validated by browse, a set of columns or filter state, and a row limit or export mode. They should return simple Python structures, Arrow batches, a temporary file path, or a streaming response body, not pandas DataFrames.

Fourth, replace the HTML preview path in `flow.py`. The preview should read only enough rows and columns to render the table, preserving existing row caps and error messages. It must use existing path validation and filter validation. Run the browse route tests after this milestone.

Fifth, replace parquet-to-CSV export in `_download.py`. The implementation should write CSV from batches or DuckDB copy output without materializing a full DataFrame. Preserve headers, empty result behavior, filtered result behavior, content type, and download filename behavior. Add or update tests that compare CSV body content for small fixtures.

Sixth, handle D-Tale. If the current browse code only forwards a path and filter state to another service, keep it that way and ensure no pandas conversion occurs in `browse`. If `browse` currently converts to pandas for D-Tale, move that conversion out of `browse` or add an explicit follow-up if D-Tale cannot be made no-pandas within this package. The package can close only if `browse` itself no longer converts parquet to pandas.

Seventh, add observability. Log or emit structured timing/RSS measurements for parquet preview/export paths with route name, run id or safe run metadata, subpath, file size, rows returned when known, duration, and worker PID/RSS before/after. Do not log file contents, secrets, auth tokens, or untrusted query payloads directly.

Finally, validate behavior and memory. Run targeted tests first, then broader microservice tests. In a production-like environment, issue representative parquet preview and CSV/export requests and sample worker RSS before the request, immediately after, and after a short settling window. Capture the commands and results in an artifact under `docs/work-packages/20260616_browse_arrow_pandas_elimination/artifacts/`.

## Concrete Steps

Start every implementation session from:

    cd /home/workdir/wepppy
    git status --short

Inventory call sites:

    rg -n "to_pandas|read_parquet|pd\\.|pandas" wepppy/microservices/browse tests/microservices

Expected initial finding includes production references in:

    wepppy/microservices/browse/_download.py
    wepppy/microservices/browse/flow.py

Run focused tests before changing behavior to establish the current baseline:

    wctl run-pytest tests/microservices/test_browse_routes.py
    wctl run-pytest tests/microservices/test_download.py
    wctl run-pytest tests/microservices/test_browse_dtale.py

After each milestone, run the same focused tests. Before handoff, run:

    wctl run-pytest tests/microservices --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260616_browse_arrow_pandas_elimination

For the final code-search gate, run:

    rg -n "to_pandas|read_parquet|pd\\.|pandas" wepppy/microservices/browse

The final result should not show pandas parquet reads or Arrow-to-pandas conversion in production browse request paths. If imports remain for unrelated reasons, document why in the tracker and keep the scope narrow.

## Validation and Acceptance

Functional acceptance requires route-level tests to pass. A human should be able to browse a parquet artifact, apply an existing parquet filter, download parquet, export CSV, and launch D-Tale without visible contract changes.

Performance acceptance requires evidence that representative parquet preview/export requests do not leave a `browse` worker with retained RSS above the package threshold. Set the initial threshold during Milestone 1 after measuring baseline fixture size; for production-like validation, the target should be materially below the June 16 failure signature of tens of GiB and should settle near normal worker baseline within the chosen observation window.

Security acceptance requires the dedicated security artifact to be complete with no unresolved medium/high findings. Path traversal, run-scope authorization, safe error handling, and subprocess behavior, if any, must be explicitly reviewed.

Documentation acceptance requires updating the browse README or schema docs to explain the no-DataFrame parquet path and updating the incident report or package artifact with final mitigation evidence.

## Idempotence and Recovery

The work should be additive until tests pass. Avoid deleting old helper code until the route-level tests prove the new helper is wired. If a route change fails, revert only the specific new helper or route patch made in this package, not unrelated user changes.

Do not weaken existing path validation to make tests pass. If a batch/streaming helper needs a temporary file, place it in an existing approved temporary location, clean it up deterministically, and document cleanup behavior. If subprocess isolation is added, invoke commands without a shell and bound concurrency, timeout, file size, and output paths.

## Artifacts and Notes

Create final validation artifacts under:

    docs/work-packages/20260616_browse_arrow_pandas_elimination/artifacts/

Suggested artifacts:

- `inventory.md` with call sites, replacement decisions, and behavior parity notes.
- `rss_validation.md` with worker RSS samples before/after representative requests.
- `20260616_security_review.md` completed from the scaffolded template.

Keep large logs out of git. Summarize only the lines that prove acceptance.

## Interfaces and Dependencies

Use dependencies already present in the runtime image. `docker/requirements-uv.txt` currently pins pandas and PyArrow for the overall project, but this package must not add new dependencies without following `docs/standards/dependency-evaluation-standard.md`.

Preferred interfaces:

- A helper that reads parquet schema without pandas and returns column metadata for templates.
- A helper that returns preview rows as plain Python lists/dicts with bounded row count.
- A helper that writes or streams CSV from parquet batches without creating a DataFrame.
- A helper that applies the existing parquet filter contract by reusing or extending `wepppy/microservices/parquet_filters.py`.

The route handlers should continue to own authentication, path resolution, and response construction. Helper functions should assume they receive an already authorized path and still validate file type, row limits, and filter compatibility.

## Plan Revision Notes

- 2026-06-16 18:58 UTC: Initial ExecPlan created during work-package scaffold. The plan captures the incident motivation, current known call sites, milestone sequence, and acceptance gates.
- 2026-06-16 19:10 UTC: Updated plan after implementation of Arrow-backed preview/CSV helpers, D-Tale bridge inventory, request-path RSS logging, and focused test validation.
- 2026-06-16 19:24 UTC: Updated plan after local Gunicorn RSS validation, logger visibility fix, broad microservice validation, changed-file broad exception gate, and security review closeout.
