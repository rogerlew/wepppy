# Roads project render contention repair (2026-10-27)

Reported instance: `clogging-starch`, config `disturbed9002-wbt-mofe`, on
`wepp.cloud`. `runs0_pure.htm` included `roads_pure.htm`, which called
`Roads.query_summary()`. Its inspection decorator attempted a shared flock while
an exclusive operation was active, raising `RoadsResultsUnavailable` and turning
the whole project page into HTTP 500.

Scope: remove result admission from project input-form rendering. The operator
explicitly required the project to load during Roads operations. No model-result,
mutation, persisted-schema, or deployment change is included.

Authority: [lifecycle contract](../schemas/roads-preparation-lifecycle-contract.md),
Replacement and invalidation item 6 (baseline independence), and Implementation
admission and retention contract (model UI may explain unavailability). This is
a conformance repair, not a new result-admission policy. Durable rationale is in
the Roads specification's public controller surface; user/operator guidance is
in the Roads README's Operational Notes.

Precedent: the 20261022 Roads preparation lifecycle package introduced admission;
the October 26 filesystem-transparency amendment separated diagnostic access
from model-result admission. This repair applies the same distinction to saved
form inputs. No retry, busy placeholder, or exception fallback is necessary.

## Bounded consumer assessment

Search boundary: repository Python and Jinja callers of Roads summary inspection,
their calling routes, and shared HTTP exception handlers.

| Consumer | Dependency and disposition |
| --- | --- |
| Project page | Confirmed defect: Jinja directly invoked guarded summary. Now uses saved inputs only. |
| Dynamic project sections | Same `roads_pure.htm` template; receives the same repair. |
| Roads API/report consumers | All remaining summary callers are in `nodb_api/roads_bp.py`, covered by the authorization/error decorator that translates lifecycle conflicts to HTTP 409. Result admission remains intentional; production behavior not exercised here. |
| Generic browse/download | No summary call; governed separately by the filesystem contract. No changes. |

## Regression evidence and rollout

`test_roads_form_renders_without_result_admission` uses a real Roads controller
and OS flock. While exclusive admission is held, the previous summary call
raises the exact busy error and the actual template renders successfully.
Coverage includes empty and populated inputs, absent lifecycle state, contention,
and malformed receipts. Populated cases verify saved filename, mapping, and
surface selection. Existing no-controller rendering covers an unused feature.
No output artifacts are produced or changed by this repair.

Validation: 312 focused Python tests passed across templates, Roads routes,
lifecycle, and controller tests; frontend lint and 1,017 frontend tests passed.
Documentation lint, diff whitespace, and changed broad-exception checks passed.
The full Python sweep was intentionally interrupted in the unrelated disturbed
model matrix after 383 passed and 27 skipped; it is not a complete-suite pass.
The bounded repair's four focused modules completed in full.
Production deployment and live project reload remain
unverified; local success is not a claim of incident recovery.

Health signal after rollout: project reload succeeds during active Roads work.
Recurrence of this stacktrace requires checking for another result reader in the
page-render path. Preserve the real-lock regression; no temporary mitigation
needs retirement.

## Publication provenance follow-up (2026-10-29)

The CI baseline's exact-source-drift check caught the missing receipt update for
commit `2fff37a75`. Inspection from the previously reviewed `8593a2995` source
shows only the additive `query_inputs` method above. The current stale-evidence
receipt now records that reviewed source delta and its predecessor hash.
Historical report bytes, result values, execution provenance and the explicit
full-project routing staleness notice are unchanged. This acknowledges the
render-only repair; it does not certify fresh routing results.

Follow-up validation: publication-provenance and real-lock form-render tests
passed (9 selected cases). No test assertions or model outputs were changed.
