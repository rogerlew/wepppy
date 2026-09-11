# M1/M3 wiring validation

Status: passed, 2026-09-11 UTC. Contract ancestor aa30e637e.

## Automated checks

- Focused Python: 117 passed across production/routes/OpenAPI/migration before
  the final migration-resume refinement; migration 24 passed afterward.
- Final route regression: 30 passed. The first full run found an assertion
  against a stale in-memory fixture after the facade refreshed its singleton.
  Affected route/production assertions now read durable state, and publication
  fixture setup reacquires its controller before direct writes. Route 30,
  production 51 and publication 13 passed. Final `wctl run-pytest tests --maxfail=1`: **8,468 passed,
  103 skipped**, 971.50 seconds. All failures were resolved; no extra deselections.
- npm: 111 suites, 872 tests passed; lint passed, including initial restoration
  and exact bounded selection retry/exclusion/order/destruction checks.
- Go preflight tests passed. RQ graph current; test stubs complete.
- Changed broad-exception gate passed. Scoped module/package documentation lint passed.

## Real state contention

Run check_contention.py through wctl exec as the development service identity.
Disposable private project model-wiring-check-a0588d15, UID 1000/GID 993:
worker phase update and artifact publication each waited for an overlapping
preference save, then preserved both changes. Accepted file bytes matched the
retained attempt files. No lock clearing, stale-object retry or hidden output.

The first fixture arrangement reused an obsolete reference after an earlier
cache refresh. Reacquiring the controller before arranging the second case fixed
the harness. Production writers resolve the authoritative singleton after waiting
for the shared gate; both operations passed against real Redis and NoDb files.

## Development browser and job tree

Target: addicted-reservist/config on wc.bearhive.duckdns.org; no other host deployment.
Credentials remain in gitignored docker/secrets/dev-agent.env. browser.cjs uses
the real form's model and Run event handlers, session-token transport and RQ.

M1 submitted through the new /run route:
job 0dafd6e9-305d-4d0d-b664-07ec780a8d49,
attempt 23236a2e9dcf4a2492204fd09dc64311.
Canonical get_wepppy_rq_job_info confirms run_m1_rq, finished,
2026-09-11 21:03:42–21:03:59 UTC, no children. Result model M1 remains current.
This validates the existing pipeline; missing-support probabilities remain
unavailable until the separately planned valid-support numerical increment.

An earlier browser used the pre-rebuild bundle and dispatched the legacy
/run-m1 route (d0b564eb-3a6b-440a-9214-b04e2ad7641d), which completed. Verified
termination before another submission. The final combined browser run saved both selections and dispatched M1
job 2fc8d67a-6436-4408-8a0a-49cdca0127b1 (finished) and M3 job
6259b9ab-b249-4edc-a4ac-bdab669df5e0 (failed integration_pending). Reload
preserved M3 selection, job ID/error, hidden dNBR/K and visible Soils; M1
results remained current and labeled M1. Canonical job_info confirms both
dedicated function names and no child jobs. Worker UID 1000/GID 993 matches all
four published files; failed M3 retains a visible error.log. Preflight retains
M1 identity and accepted timestamp after M3 selection/failure.

Early headless checks stalled while the software WebGL renderer consumed over
1000% CPU; collapsing Map and focusing the debris-flow control enabled the
combined browser checks without changing application logic. Fast selection
before initial state restoration exposed a rainfall-default overwrite; the UI
now disables selectors until restoration, with a delayed-state regression.
Final delayed-load readback passed with recording enabled: the busy sequence
409/409/409/200 saved M3/NOAA, followed by successful M1/NOAA and M3/NOAA saves.
Reload retained M3/NOAA, hidden dNBR, job ID and explicit failure. The preflight
WebSocket reported postfire_debris_flow=true for the accepted M1 result, and
manifest download returned 200. The job count did not change during selection.
Retained evidence: browser_readback.log, live_job_trees.json and control_m3.png.
The bounded conformance mechanism and recurrence criteria are documented in
selection_contention.md and the canonical selection contract. Recording and
shared admission remain enabled.

## Remaining scientific work

M3 soil/terrain composition and probability output are not delivered here.
The dedicated task must report integration_pending. Shared valid-support
aggregation, valid_mask.tif and coverage values are the next scientific increment;
the UI accommodates metadata but does not invent it. No report/dashboard added.

Final independent correctness and security reviews accepted the source and
retained runtime evidence, conditional only on the full Python pass. That
condition is satisfied. No production host deployment or push was performed.
