# Scoped regression and acceptance tests

This matrix is the test scaffold. Implementation milestones add and run the executable cases. Use disposable project data with real Parquet and catalog files, real Redis/RQ for admission, and a compatible default worker for browser acceptance. Keep timing assertions tied to deterministic barriers, allowing enough time for the test environment.

## Valid catalog and worker states

| State | Expected evidence |
| --- | --- |
| Missing catalog or never queried | Preparation records one repair intent and admits one job. Concurrent callers and later polls leave the receipt count stable. |
| Valid empty catalog or optional dataset absent | Query discovery follows the existing missing-data path. GL avoids a refresh loop. |
| Populated current or valid legacy catalog without sidecar | GL sends its queries promptly. No worker job or full scan starts. |
| Pending, running, or backoff | Both tabs show preparation, continue to use the map, and hold result requests. Rate of status requests respects the server interval. |
| Catalog published with residual receipts, replaced incarnation, or job complete with unreadable catalog | Status and queries avoid premature success. A new receipt survives the earlier refresh acknowledgment. |
| Malformed catalog or corrupt required source | Existing authorized repair or explicit bounded failure. Prior good artifacts remain readable where allowed. |
| Readonly current and readonly repair required | Current reads succeed. Repair-required state returns an explicit error and creates no receipts, queue entries, or catalog writes. |
| Async disabled or supported unmanaged | A usable catalog still queries. Repair required yields typed unavailable without worker admission. |
| Old failed attempt with viable retry | Current incarnation and viable retry drive preparation. Old failure does not mask readiness or active retry. |
| Redis/worker unavailable, terminal failure, or wait deadline | Visible explanation and Retry. No inline scan, duplicate job, or empty WEPP panel presented as missing data. |

## Input and concurrency coverage

| Boundary | Scoped cases and assertions |
| --- | --- |
| HTTP/access | Authorized private and public ordinary runs, nested Omni/batch target, wrong principal, malformed selector, cross-origin cookie POST, and aggregate-path and symlink containment. Denied calls leave filesystem and Redis state intact. Verify status responses expose no internal scope, path, receipt, job or exception details. |
| Publisher and admission | Start concurrent preparations before a catalog exists. Gate the worker to prove one receipt and admission. Inspect real publication and inject a late receipt before acknowledgment. Recheck after a lifecycle change. Probe a stale sidecar with an otherwise readable catalog, an independently held lifecycle lock, and bounded Redis failure. Run the real worker with both a permitted inherited source and a contained-policy rejection for a sibling path. |
| SQL entry points | Inject invalidation once after ready and again between context preparation and execution. In wait mode, assert a typed pending response before SQL or inline refresh. Change a real source without writing a producer receipt and prove repair completes, then reissue SQL. Verify unchanged successful response bodies for synchronous callers and existing missing-dataset and Roads error handling. |
| GL client | Hold startup, graph and user-initiated requests on one promise per target. Test independent base/comparison targets, scenario switch during a wait, server-directed polling, cancellation or deadline, and recovery via Retry. Fail the test if pending is treated as an empty query result. |
| Served browser and artifacts | Open two tabs against the same disposable NFS-backed run with a pending refresh. Capture browser request ordering, visible status, job/admission evidence and catalog contents. Release the worker and verify a deterministic known WEPP value from the selected Parquet source in Query Engine output and the corresponding rendered map layer in both tabs. Repeat with a late invalidation and a worker failure. Clicking Retry must reload the original layers without page reload. Verify that an already-ready comparison target still renders while the other target waits. |

Run the focused Python suite from the task checkout after adding the cases.

    wctl run-pytest tests/query_engine/test_http_access_boundary.py tests/query_engine/test_catalog_refresh.py tests/rq/test_query_catalog_rq.py tests/rq/test_query_catalog_disclosure.py --maxfail=1

Add client cases to `wepppy/weppcloud/static/js/gl-dashboard/__tests__/query-engine.test.js`. From `wepppy/weppcloud/static-src`, use the installed Jest and Playwright tools against the task source and its disposable stack.

    NODE_OPTIONS=--experimental-vm-modules npm exec -- jest --config jest.config.mjs --testPathPatterns=gl-dashboard/.*/query-engine
    npm run smoke -- tests/smoke/gl-dashboard-catalog-readiness.spec.js

For real RQ tests, use an isolated Redis server with TCP disabled and mount its
Unix socket into the disposable candidate container. Seed the
`batch-boundary-test-server` key with `disposable` and set
`BATCH_BOUNDARY_TEST_REDIS_SOCKET` inside that container to the mounted socket
path. Check that pytest executes the real admission tests.

For the browser spec, set `GL_CATALOG_TEST_URL` to the served disposable run,
`GL_CATALOG_TEST_TOPAZ_ID` to the fixture hillslope, and
`GL_CATALOG_TEST_RUNOFF_MM` to its known runoff value. Start with pending
publication so both tabs observe preparation. The validated fixture used NFS,
hillslope 11 and 10 mm. Playwright held the status responses until both tabs
asserted zero result POSTs, then checked the active runoff layer. The companion
RQ test supplies scheduler and worker evidence. Retain the checkout, runtime
identity, and sanitized request timing alongside artifact readback. Also run repository-required broader gates before a production handoff. Use `wctl check-rq-graph` and inspect a live job tree if implementation changes enqueue wiring.
