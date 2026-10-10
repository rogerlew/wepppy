# Return-period Omni validation

Date: 2026-10-10 UTC. Implementation working tree follows contract commits
`c5358daa7` and `946ec76fb`; generated docs_index.json excluded throughout.

## Evidence chain

Request selections → real staged event/rank Parquets → existing report reader →
actual Jinja report → actual CSV response bytes. Tests deliberately offset child
calendar years and runoff values so accidentally reusing parent data fails.
HTML/CSV comparisons include exclusions and parent preferences in mm/inches;
HTML retains normal rounding while CSV retains full numeric precision.

No model inputs or stored output schemas change. Source datasets are fixture
copies, not new model simulations. NoDb/auth doubles isolate unrelated services;
real filesystem containment, Parquet parsing, ranking, unit conversion, template
and CSV serialization are exercised. Archive/restoration test uses an actual tar
round trip and checks shared-input contents and restored discovery.

## Checks

| Check | Result |
| --- | --- |
| Focused route/discovery/template pytest | 285 passed after review fixes; six final date/invalid-calendar/real-URL regressions also passed |
| Frontend Jest | 114 suites, 931 tests passed |
| Frontend lint | Blocked by unchanged climate.test.js:300 conditional expect; changed return_period_inline.test.js lint passes |
| Controller bundle build | Passed through `wctl exec weppcloud python .../build_controllers_js.py`; no generated bundle diff |
| Stub hygiene | `wctl check-test-stubs` passed |
| Full pytest sanity | `wctl run-pytest tests --maxfail=1` running; model matrix in progress |
| Documentation lint | Contract, package, report note and route README passed; final status edits rechecked before handoff |
| Broad-exception enforcement | Line-based allowlist drift reports +1; AST verifies 26 broad handlers before and after, none added |
| Code quality observability | Observe-only report produced; working-tree deltas unavailable in this tool's report |

The broad-exception tool counted an existing shifted `query_bound_coords` handler
as newly unsuppressed after lines were inserted above it. No new broad catch was
introduced. The smallest tooling follow-up is stable handler identity rather than
line-only allowance matching; no unrelated allowlist rewrite is included here.

## Browser smoke

Chromium, 1280×1000 and 390×844, fixture Flask server using the real route,
report template, shared CSS and `report_csv.js`. Passed: default unchecked,
two selections applied and preserved on reload, six independent table/CSV rows,
download action, year exclusion, AM/month selection, extraneous round trip,
clearing all selections, and no horizontal document overflow at 390px.
Page errors: zero. Screenshots: `configuration.png`, `comparison-table.png`.

Auth/NoDb loading and shared shell were isolated. This proves the local report
workflow, not production authentication, runtime identity, or deployment.
Temporary fixture server is stopped after smoke verification.

## Completion boundary

Implemented, focused/local browser validated, independent correctness/security
reviews approved. Full sanity result pending. Not
deployed; no production scenario outputs changed or repaired.
