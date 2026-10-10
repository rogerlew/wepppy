# Forest flow-duration validation

Date: 2026-10-10. Checkpoint ancestor: c63f2cc52. Implementation commit recorded
at handoff. Host: forest; installed wctl preset docker/docker-compose.dev.yml.
No model output or persisted schema mutations.

## Source-to-browser evidence

Authenticated browser target:
https://wc.bearhive.duckdns.org/weppcloud/runs/eighty-five-synthetic/disturbed9002_wbt/gl-dashboard

`source_oracle.py` reads the actual Parquets independently using DuckDB and retains
SHA256 source hashes in `source_oracle.json`. Network root Topaz 24 translates to
Chan_ID 128 / Elmt_ID 412; both are used to select ledger rows. The 1980–2024 source
records contain 16,437 daily rows. Excluding 1980/1981 retains 15,706 rows. The browser
matches oracle minimum/maximum flow and exact N for all four scenario/source
combinations, with zero missing dates. `browser_evidence.json` retains displayed
labels/colors, periods, ranks and request counts. No authentication values are
included. The implementation retains values even when a scenario has a different
period; independent-period unit fixtures cover this case.

Two authenticated Playwright tests pass: parent comparison and standalone Omni
child (`?pup=omni/scenarios/undisturbed` and terminal `;;omni;;undisturbed`). Checks
cover both sources, linear/log probability axes, default two-year and explicit
all-year selection, hover discharge/probability, keyboard inspection, resize,
no redundant query on scale changes, exact child labels and console errors.
`/tmp/fdc-dashboard.png` was visually inspected: distinct red Burned / green
undisturbed curves, readable axes, controls and per-scenario metadata.

## Test gates

- Full Jest: 117 suites, 951 tests passed. Focused final FDC suite: 18 tests.
- Final targeted route/boundary pytest: 32 passed, including filesystem/symlink
  ownership, stale catalogs, malformed real Parquet, shared topology, child URLs
  and terminal Omni-run identifier selection.
- Full Python suite: running; outcome to be appended before handoff. It began
  before the final child/coverage corrections; final focused tests cover those
  corrections directly.
- `wctl run-npm lint`: existing failure in controllers_js/__tests__/climate.test.js
  line 300, jest/no-conditional-expect. No changes to that test.
- Scoped Markdown lint and changed broad-exception inventory pass. Code-quality
  observability completed (non-blocking).

Existing GL graph/layout/layer/state smoke suite: 30 passed, 14 skipped, 3 failed.
The failures are comparison-mode selector/legend and missing raster labels
Landuse (nlcd.tif), Soils (ssurgo.tif). All three reproduce when browser requests
for gl-dashboard.js and every gl-dashboard module are served verbatim from
checkpoint c63f2cc52 via Playwright route interception, against the same authorized
project and backend. This establishes pre-existing frontend behavior for these
checks; it is not a claim those unrelated failures are repaired. Temporary test
copies, configuration and the mode 0600 authentication state were removed afterward.

## Restart and operational check

Ran installed `wctl restart` for the forest development Compose stack, without
image publication, branch changes or a registry workflow. Follow-up changes to
Python metadata were loaded with Gunicorn master HUP. All 25 application services
were running; download, PostgreSQL, PostgreSQL backup and Redis health checks
were healthy. Build helper containers are one-shot services and not counted as
running applications. Public authenticated workflow passes after restart.

## Performance and limits

`benchmark.mjs` / `performance.json`: 20 synthetic scenarios × 45 years ranked in
about 1.00 second, cached axis load 0.21 ms; 3 scenarios × 500 years ranked in 1.58 seconds,
cached axis load 0.05 ms. These are Node loader measurements with in-memory query
fixtures; network/real browser costs and GC variability are not included. Ranking
always uses every eligible observation and display does not truncate tails.

Rain-on-snow control and explanation are omitted per the final operator decision. Fixed metric units and
baseline output scope only are the accepted first delivery. Reload after model
regeneration because source provenance and cache contents are page snapshots.

Independent final correctness, QA and security reviews passed; all six security
findings are resolved. Retained review artifacts record independent checks.
