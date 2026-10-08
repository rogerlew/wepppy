# Implement historic PRISM bulk extraction and persistent caching

Outcome: delivered the bulk client/cache and Docker configuration; validation limitations and remaining climate integration are recorded below. No deployment or commit was performed.

This completed plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Enable Python callers to extract daily PRISM data for multiple CONUS points, deduplicate points in the same native cell, and reuse validated data across projects. Operators choose persistent cache storage with Docker `.env`. This is production client code, separately callable and validated; it is not wired to climate modes or WEPP builds.

## Progress

- [x] (2026-10-08 UTC) Inspect prior evidence, climate clients and Docker environment/mount contracts.
- [x] (2026-10-08 UTC) Implement native mapping, protocol/parser, revision checks and immutable cache with atomic references.
- [x] (2026-10-08 UTC) Wire Docker defaults/shared environments and local `.env`; publish API/cache contract and ADR-0081.
- [x] (2026-10-08 UTC) Complete 39 focused tests, live worker artifact checks, correctness review, API/stub and documentation checks. Full suite: 10,253 passed, 126 skipped, one unrelated latency failure; failed module plus remaining tail rerun: 207 passed.

## Surprises & Discoveries

The broad suite encountered a timing-sensitive PostgreSQL marker-write test (64 ms incremental p95 against a 50 ms limit). The entire unchanged module passed on rerun; this is recorded as a validation limitation, not a PRISM regression fix.

Legacy `ObservedPRISM` routes to Daymet. Legacy direct PRISM uses 4 km interpolated requests and clips dewpoint. Neither is changed here. Bulk can silently omit masked cells and releaseDate can return HTTP-200 non-JSON errors. These are confirmed protocol hazards from the retained investigation. First live worker polling hit a dropped connection at the provider five-second keep-alive deadline. Retained the failed attempt and disabled socket reuse; direct rerun completed in 7.0 seconds cold and 3.1 seconds warm with exact prior-source parity.

## Decision Log

2026-10-08 UTC, user/Codex: nearest native cell, no interpolation; Docker `.env` specifies `PRISM_CACHE_DIR`. Default `/wc1/cache/prism` uses an existing persistent mount. Always recheck release metadata on cache use, avoiding a speculative TTL. Dates partition at calendar years, retaining exact partial intervals rather than merging overlapping caches. Serialize cache operations with bounded POSIX file locks; immutable attempts plus atomic entry pointers avoid partially published data. No new infrastructure.

## Outcomes & Retrospective

Implemented the additive raw bulk API, native-cell cache and Docker configuration. Live worker extraction/reuse and retained source parity pass. The broad suite stopped after 10,253 passing tests on an unchanged PostgreSQL latency threshold; its full module passed on rerun. Final tail-suite outcome is recorded in the tracker and validation summary. No deployment or climate-mode integration occurred. Provider keep-alive expiration required closing HTTP connections, and measured mapping/parser bottlenecks were removed without changing values.

## Context and Orientation

`docs/dev-notes/prism-800m-client-design.md` is the durable scientific/data contract. The prior bulk investigation proves native 800 m extraction and 500-cell year requests. Add modules under `wepppy/climates/prism/` and tests under `tests/climates/prism/`. Existing `daily_client.py` remains untouched. The API accepts named longitude/latitude points and ISO start/end dates, returns raw per-cell daily tables, point-to-cell mapping and immutable source provenance. Do not clip dewpoint, convert radiation, disaggregate rain, or introduce UI controls.

## Plan of Work

First define native NAD83 grid indexing and strict protocol parsing. Bulk submission uses `pp/daily_timeseries_mp`, polls `pp/checkup`, and downloads only a validated relative path under the provider's Explorer temporary directory. Extract five fields: ppt, tmin, tmax, tdmean, soltotal. Require exact requested dates and cells and valid source units. Request complete releaseDate manifests for each field before/after fresh acquisition.

Next add cache attempts with status, requests, HTTP evidence, raw CSV and per-cell parquet. Compare normalized manifests before reusing entries. On revision races retain failed attempt and retry at most once. Publish per-cell references atomically only after validation; never replace immutable attempts. Bound lock/network waits and record failure diagnostics. Fail clearly on cache corruption and freshness errors.

Then add `PRISM_CACHE_DIR` to committed Docker defaults and the shared dev/prod/worker environment mappings, preserving current mounts/identities. Add the non-secret override to local ignored `.env` without exposing or rewriting other settings. Document that custom paths must already be mounted and writable by the service identity.

Finally test malformed responses, nodata omission, dates/leap days, native cell ties, deduplication, batching, revision changes, partial publication and concurrent cache access using real temporary filesystem artifacts and deterministic transport fixtures. Run live cold and warm extraction in the running Compose service on the mounted cache path. Compare values and checksum provenance; no deployment or service recreation is required for scoped exec validation.

## Concrete Steps

From `/home/workdir/wepppy`, run `wctl run-pytest tests/climates/prism -q`, then `wctl run-pytest tests --maxfail=1`. Use `wctl exec -T` with the configured cache variable for a live study script retained under this package's `artifacts/`. Validate rendered Compose environment without printing secrets. Lint modified Markdown with `wctl doc-lint --path`.

## Validation and Acceptance

Verify actual downloaded CSVs and persisted parquet through the production reader. A same-cell alias must share exactly one series. Warm retrieval must perform manifest checks but no bulk extraction. A changed manifest must fetch replacement data while old provenance remains readable. Unchanged before/after manifests support conservative freshness only, not atomic provider revision proof. All parser/cache failure fixtures must fail explicitly and leave no falsely current entries. Record container identity, mount, umask, path and actual semantic comparisons. Model/PRN/CLI readback is not applicable because this scope does not produce model inputs.

## Idempotence and Recovery

Attempt records survive failures. Locks release on process exit. Entry replacement is atomic; incomplete attempts are never selected by entry pointers. Cache corruption is an explicit operator error, not silently served or deleted. Keep prior successful attempts and references; retry failed requests normally. No source projects or closed packages are modified.

## Artifacts and Notes

Retain concise live evidence, test outcomes and correctness review. Raw shared cache data reside under the configured directory; consumer project snapshot/archive wiring remains a future requirement. Preserve prior scientific studies as immutable history.

## Interfaces and Dependencies

Use `PrismBulkClient.retrieve(locations, start_date, end_date)` and native grid cell IDs. `PRISM_CACHE_DIR` must be an absolute path or explicitly supplied to the constructor. Reuse installed geospatial libraries for coordinate transformation; Python only orchestrates point mapping, HTTP, tabular parsing and caching. No raster processing replacement or added dependencies.

Initial revision 2026-10-08 UTC: implement the user-authorized bulk extraction/cache slice.

Revision 2026-10-08 UTC: implemented client/cache and Docker path, first 29 tests pass, live worker identity/mount cold/warm readback passes after fixing the observed keep-alive boundary. Full regression and expanded failure tests remain running.

Final revision 2026-10-08 UTC: completed real worker and 500-cell parser validation, failure/concurrency tests and documentation. Retained the broad-suite latency failure and successful 207-test tail rerun. Closed this extraction/cache scope.
