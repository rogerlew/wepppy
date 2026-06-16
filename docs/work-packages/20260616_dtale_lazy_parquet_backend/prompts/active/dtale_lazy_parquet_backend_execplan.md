# Implement Lazy Parquet Loading for D-Tale

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`. It is self-contained so a future contributor can implement the package from this file and the repository tree alone.

## Purpose / Big Picture

WEPPcloud users can open run output tables in D-Tale from the browse UI. For Parquet files, the D-Tale service currently reads the entire file into a pandas DataFrame before showing the grid. That can recreate the high resident memory problem that the browse service mitigation removed, just in a separate long-lived D-Tale worker.

After this change, opening a Parquet file in D-Tale should register a lazy backend that reads only the rows and columns needed for the visible grid page. D-Tale can still use small pandas slices internally because the upstream formatter expects pandas, but the service must not convert the whole Parquet file into pandas up front. The visible proof is that `/internal/load` returns a normal D-Tale URL and `/dtale/data/<id>` returns grid rows from a Parquet fixture without the eager `_load_dataframe` path being called.

## Progress

- [x] (2026-06-16 19:51 UTC) Work-package scaffold and initial ExecPlan created.
- [x] (2026-06-16 20:10 UTC) Inventory the exact D-Tale 3.20.0 lazy-backend seam and local eager Parquet paths.
- [x] (2026-06-16 20:10 UTC) Implement a local lazy Parquet instance/backend.
- [x] (2026-06-16 20:10 UTC) Wire Parquet `/internal/load` to register lazy datasets.
- [x] (2026-06-16 20:10 UTC) Patch or adapt D-Tale data-route behavior narrowly for lazy Parquet datasets.
- [x] (2026-06-16 20:16 UTC) Add focused tests for lazy registration and paged row loads.
- [x] (2026-06-16 20:16 UTC) Update D-Tale service notes and package tracker.
- [x] (2026-06-16 20:16 UTC) Run validation and capture outcomes.

## Surprises & Discoveries

- Observation: D-Tale's `data_loader` hook is not lazy in version 3.20.0; it is called immediately and still expects a pandas DataFrame.
  Evidence: Installed `dtale.views.startup` source shows `data = data_loader()` before normal startup validation.

- Observation: The existing parquet filter compiler already exposes DuckDB-safe `WHERE` SQL and parameters.
  Evidence: `wepppy/microservices/parquet_filters.py` returns `CompiledParquetFilter(where_sql, params, summary)`, and the lazy backend now uses it for filtered D-Tale launches.

- Observation: Distinct filtered D-Tale datasets originally shared the same display name and upstream D-Tale rejected the second load.
  Evidence: Focused test initially failed with `Exception: Name run-1/default/table.parquet [filtered] already exists!`; the loader now appends an eight-character filter hash to filtered display names.

- Observation: D-Tale's grid export path can request all rows through `/dtale/data/<id>?export=true`.
  Evidence: The lazy route now returns HTTP 501 for lazy Parquet export and directs users to the already hardened browse CSV export path.

## Decision Log

- Decision: Use a D-Tale lazy-backend adapter modeled on ArcticDB rather than a broad D-Tale fork.
  Rationale: D-Tale is explicitly pandas-first, but upstream already has a reduced-functionality lazy path for ArcticDB that pages rows and columns. Mirroring that seam minimizes drift and keeps WEPP-specific Parquet logic outside upstream D-Tale code.
  Date/Author: 2026-06-16 19:51 UTC / Codex.

- Decision: Seed upstream D-Tale with a one-row pandas sample and keep authoritative grid reads in a separate lazy registry.
  Rationale: `startup` still needs pandas-shaped metadata to build the D-Tale shell. A one-row sample avoids full-table conversion while preserving D-Tale URLs, settings, dtypes, and existing map metadata hooks.
  Date/Author: 2026-06-16 20:10 UTC / Codex.

- Decision: Remove Parquet from the eager `_load_dataframe` dispatch.
  Rationale: Even if the main loader is lazy, leaving a Parquet reader in the eager dispatch creates an easy future regression path back to `pd.read_parquet`.
  Date/Author: 2026-06-16 20:16 UTC / Codex.

- Decision: Support simple D-Tale grid sorting with DuckDB `ORDER BY`, but reject lazy D-Tale export.
  Rationale: Sorting is a bounded grid operation and can be pushed into DuckDB safely. Export can ask for all rows and would reintroduce large pandas conversion; browse CSV export is the supported large export path.
  Date/Author: 2026-06-16 20:16 UTC / Codex.

## Outcomes & Retrospective

Implementation is complete locally. Parquet, GeoParquet, and PQ files now register a `LazyParquetDtaleInstance`; `/dtale/data/<id>` is intercepted only for those lazy IDs and reads bounded row/column windows through DuckDB/PyArrow. Filtered Parquet launches remain lazy via the existing parquet filter compiler. Non-Parquet files continue through the existing eager pandas D-Tale path. Production observation remains as an operational follow-up if this implementation is deployed.

## Context and Orientation

The relevant WEPPpy service is `wepppy/webservices/dtale/dtale.py`. It embeds the upstream D-Tale Flask app, adds `/health`, and adds `POST /internal/load`. The browse microservice calls `/internal/load` after it has authorized a run and resolved a run-relative path. The D-Tale service then resolves the path again inside the run directory and loads the file into D-Tale.

Current eager Parquet behavior lives in `_read_parquet`, `_load_dataframe`, and the filtered branch inside `load_into_dtale`. `_read_parquet` calls `pd.read_parquet(path)` and `_postprocess_dataframe(df)`. The filtered branch calls `query_filtered_parquet_export(...)` and then `filtered_table.to_pandas()`. `_initialize_dtale_dataset` passes the resulting DataFrame to upstream `dtale.views.startup`.

D-Tale is a Flask/React grid for pandas data structures. Its `startup` function can accept `data_loader`, but in D-Tale 3.20.0 that hook is called immediately and must return a pandas DataFrame, so it is not the lazy solution. D-Tale also has an ArcticDB integration. In that mode, D-Tale stores an instance with `rows(...)`, `load_data(row_range=..., columns=...)`, `base_df`, and `is_large`, and the `/dtale/data/<id>` route asks the instance for visible rows and columns. This package uses that shape locally with DuckDB or PyArrow reading from Parquet.

A "lazy backend" in this plan means an object that knows the Parquet path and can return only a bounded row/column window. It may return a small pandas DataFrame for the requested window because D-Tale's grid formatter expects pandas, but it must not read or retain the entire Parquet file as pandas.

## Plan of Work

First, inspect the installed D-Tale 3.20.0 source in the local `wepppy-dtale` container or the runtime image. Confirm the current signatures and source snippets for `dtale.views.startup`, `dtale.views.get_data`, and `dtale.global_state.DtaleArcticDBInstance`. Record any relevant discoveries in this plan and `tracker.md`.

Second, add a small local module or section in `wepppy/webservices/dtale/dtale.py` that can register lazy Parquet datasets. The simplest implementation should include:

- a registry mapping D-Tale `data_id` to lazy Parquet metadata;
- a `LazyParquetDtaleInstance` class with `rows()`, `load_data(row_range=None, columns=None, **kwargs)`, `base_df`, `is_large`, and `data`;
- helpers to read schema and row counts without pandas;
- a helper to build D-Tale dtype state from the schema and a one-row sample.

Use DuckDB if it gives simple `LIMIT` and `OFFSET` paging over `read_parquet(?)` without adding dependencies. Use PyArrow metadata for row counts and schema. Any returned pandas DataFrame must be limited to the requested page or one-row dtype sample.

Third, wire `load_into_dtale`. For Parquet files, do not call `_load_dataframe`. Instead register the lazy dataset, set the minimal D-Tale global state needed for `dtale/main/<id>` and `/dtale/data/<id>`, and return the same response shape as before. Filtered Parquet D-Tale launches use the existing `CompiledParquetFilter` DuckDB SQL fragment and remain lazy.

Fourth, adapt D-Tale's data route with the narrowest patch. Prefer a wrapper around `dtale.views.get_data` that checks whether `data_id` is in the lazy Parquet registry. For lazy IDs, return the same JSON shape expected by the D-Tale grid using only visible columns and requested row ranges. For all other IDs, call the original upstream route function unchanged. Mark the wrapper with a `_wepppy_patched` guard as required by `wepppy/webservices/dtale/AGENTS.md`.

Fifth, guard unsupported routes. If D-Tale calls a route that would call `global_state.get_data(data_id)` and force a full Parquet load, return an explicit error for lazy Parquet IDs or keep the UI settings hiding that action where possible. Do not silently fall back to `instance.data` loading the full file.

Sixth, add tests under `tests/microservices/test_browse_dtale.py` or a new focused D-Tale test file. Tests should prove:

- `/internal/load` on a Parquet fixture succeeds without calling `_load_dataframe`;
- a registered lazy backend returns expected rows for a requested range;
- non-Parquet/eager behavior remains intact for an existing test;
- full-file `pd.read_parquet` is not needed on the unfiltered Parquet load path.

Finally, update docs and validate. Update `wepppy/webservices/dtale/AGENTS.md` with the lazy backend contract and upstream sync guard. Update this ExecPlan and `tracker.md` with exact commands run, results, and any residual risk.

## Concrete Steps

Start from a clean worktree:

    cd /home/workdir/wepppy
    git status --short --branch

Inspect local eager call sites:

    rg -n "read_parquet|to_pandas|_load_dataframe|startup\\(" wepppy/webservices/dtale tests/microservices/test_browse_dtale.py

Run focused tests before and after implementation:

    wctl run-pytest tests/microservices/test_browse_dtale.py

Current focused result:

    5 passed, 4 skipped, 4 warnings in 14.56s

Final validation results:

    wctl run-pytest tests/microservices/test_browse_dtale.py
    5 passed, 4 skipped

    wctl run-pytest tests/microservices --maxfail=1
    967 passed, 4 skipped

    wctl run-stubtest wepppy.webservices.dtale
    Success: no issues found in 2 modules

    wctl check-test-stubs
    All stubs are complete

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    Result: PASS, net delta +0

    wctl doc-lint --path docs/work-packages/20260616_dtale_lazy_parquet_backend
    3 files validated, 0 errors, 0 warnings

Run broader validation before handoff:

    wctl run-pytest tests/microservices --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260616_dtale_lazy_parquet_backend

Optional local container smoke when the stack is running:

    docker compose -f docker/docker-compose.dev.yml restart dtale
    docker exec wepppy-dtale python - <<'PY'
    import dtale
    print(dtale.__version__)
    PY

## Validation and Acceptance

Functional acceptance requires focused tests to show that Parquet `/internal/load` registers a lazy dataset and that a D-Tale grid data request returns expected rows. The tests must fail if `_load_dataframe` is required for the unfiltered Parquet path.

Performance acceptance for this package is scoped to behavior evidence: the implementation must not call full-table `pd.read_parquet` or full-table Arrow `to_pandas()` for unfiltered Parquet D-Tale loads. A production-like RSS probe is valuable but not required for the first commit if route-level evidence proves bounded reads.

Upstream-sync acceptance requires the patch to be narrow. The implementation should patch one D-Tale route or add one local route override, not copy large chunks of upstream D-Tale source. Contract tests should make upstream drift visible during future upgrades.

Security acceptance requires existing internal token verification and `_resolve_target` path traversal protections to remain in place. New helpers must assume the path was already authorized and must not introduce shell execution or external network access.

## Idempotence and Recovery

All changes are local code and documentation changes. Re-running `/internal/load` for the same Parquet file should reuse or refresh the registered lazy dataset based on the existing fingerprint logic. If a lazy registration fails, the loader should return an explicit error rather than falling back to eager full-file pandas conversion.

If tests fail after route patching, revert only the patch wrapper or lazy registration path from this package. Do not revert unrelated user changes. The existing eager non-Parquet path should remain available throughout the work.

## Artifacts and Notes

The most important evidence should be captured in:

    docs/work-packages/20260616_dtale_lazy_parquet_backend/tracker.md

If manual RSS or HTTP smoke output is collected, summarize it in:

    docs/work-packages/20260616_dtale_lazy_parquet_backend/artifacts/

Keep large logs out of git.

## Interfaces and Dependencies

Use only dependencies already present in `docker/requirements-uv.txt`: D-Tale 3.20.0, DuckDB 1.1.1, PyArrow 16.1.0, and pandas 2.2.2. Do not add ArcticDB.

The lazy instance interface should look like:

    class LazyParquetDtaleInstance:
        def rows(self, **kwargs) -> int: ...
        def load_data(self, row_range=None, columns=None, **kwargs) -> pandas.DataFrame: ...
        @property
        def base_df(self) -> pandas.DataFrame: ...
        @property
        def is_large(self) -> bool: ...
        @property
        def data(self):
            raise RuntimeError("lazy parquet datasets cannot be loaded as full DataFrames")

The route adapter should return D-Tale-compatible JSON with at least:

    {
        "results": {row_index: {"dtale_index": row_index, ...}},
        "columns": [...],
        "total": row_count,
        "success": True
    }

Use D-Tale's existing grid formatting helpers when practical, but do not copy large upstream functions.

## Plan Revision Notes

- 2026-06-16 19:51 UTC: Initial ExecPlan created during work-package scaffold. It captures the lazy-backend design, acceptance gates, and validation commands.
- 2026-06-16 20:16 UTC: Updated after implementation. The plan now records the one-row sample startup strategy, lazy DuckDB/PyArrow page reads, filtered D-Tale support through the existing parquet filter compiler, duplicate filtered-name fix, and focused test result.
- 2026-06-16 20:16 UTC: Updated after final validation. The plan now records grid sort support, explicit lazy export rejection, broad microservice/stub/doc validation, and local implementation closeout.
