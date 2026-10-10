# Return-period Omni validation

Date: 2026-10-10 UTC. Implementation commit `d252ff056` follows contract commits
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
| Full pytest sanity | 10,554 passed, 126 skipped, 5,487 warnings in 47m02s |
| Documentation lint | Contract, package, report note and route README passed; final status edits rechecked before handoff |
| Broad-exception enforcement | Line-based allowlist drift reports +1; AST verifies 26 broad handlers before and after, none added |
| Code quality observability | Committed diff observed: route length 113→157 lines; discovery helper remains green |

The broad-exception tool counted an existing shifted `query_bound_coords` handler
as newly unsuppressed after lines were inserted above it. No new broad catch was
introduced. The smallest tooling follow-up is stable handler identity rather than
line-only allowance matching; no unrelated allowlist rewrite is included here.

The existing route grows to keep its single-project and comparison responses in
one established endpoint; discovery is extracted into a small dedicated module.
A broader route split would expand this feature's regression surface. Existing
route/template test modules also grow; new discovery and JS tests are separate.
Python complexity metrics were unavailable because radon is absent.

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
reviews approved. Full sanity passed. Not deployed; no production scenario outputs changed or repaired.

## Correction after actual-project feedback

Contract ancestor `d89ace269` removes the invalid READONLY completion assumption.
Direct discovery of `/wc1/runs/ei/eighty-five-synthetic` now returns undisturbed
with `reason: null`; no original project outputs were changed.

A temporary copy of that child's actual loss/EBE/totalwatsed and climate Parquets
retained absent marker/staged tables and empty run-state metadata. Discovery
made no writes. Selection produced 16,437 staged events; emitted CSV verified
against the report reader: 5-year runoff 84.08729054474676 mm on 01/24/1995;
2-year runoff 65.84199386407387 mm on 02/26/2023 (excluded years 0,1, Gringorten).
Parent fixture rows remained alongside child rows. Auth/NoDb doubles isolate
services; no live authentication or deployment claim.

Correction validation: 91 focused pytest passed; 2 full/partial staging tests
passed; 933 Jest tests passed; bundle rebuilt. Full frontend lint retains the
unchanged climate.test.js:300 conditional-expect error. Independent correctness
and security reviewers approve against the correction ancestor.

Full Python sanity completed: 10,554 passed, 126 skipped, 5,487 warnings in
2822.38 seconds. It began before the final readonly correction; the correction
was separately exercised by 91 focused tests, two staging regressions, actual
project-copy readback, and the final 933-test frontend run. No failures.
Implementation commits: `d252ff056`, correction `99981ce36`. Not deployed.
