# Correctness and UX review: return-period Omni comparisons

Reviewer: `/root/contract_correctness`, independent read-only reviewer.
Date: 2026-10-10 UTC. Scope: route, discovery helper, template, tests and docs.
Contract ancestors: `c5358daa7`, `946ec76fb`; production changes followed both.
Authority: `docs/ui-docs/contracts/return-period-omni-scenarios-contract.md`.

## Outcome and disposition

Approved after fixes; no unresolved high/medium findings. Reviewer independently
reproduced date, empty-filter, and metric-interval issues with fixture data and
confirmed the final fixes. Parent agent implemented the fixes and tests.

| Finding | Severity | Resolution |
| --- | --- | --- |
| CSV ignored explicit calendar/display year | Medium | Comparison CSV honors each event year; tests use explicit dates, differing `y0`, and HTML/CSV readback |
| Filtering all events in one group aborted comparison | Medium | Narrow translation only after reading actual month/channel fields and proving filtering caused emptiness; parent and child covered |
| HTML iterated the first metric's intervals | Medium | Comparison rows use each metric's own keys, matching CSV |
| Empty parent lost year exclusions | Medium | Empty report retains request metadata; route and rendered selection regressions |
| Only default-unit evidence | Low | Actual-template/CSV test covers both mm and inches using parent preferences |
| Configuration screenshot initially showed tables | Low | Recaptured Configuration controls and visually inspected the image |

## State and error evidence

Absent/empty Omni remains a normal report. Modern completed, legacy completed,
missing-input, failed/incomplete, and archive/restored states have direct
filesystem coverage in `test_return_period_scenarios.py`. Escaping paths and
formula-leading arbitrary definitions fail without opening selected external
files. Valid shared parent input links remain usable.

The route tests use actual staged Parquets and report evaluation for CTA/AM,
baseline/Roads, year/month exclusions, duplicate selections, custom intervals,
missing channels, asymmetric empty groups, and warmed caches. HTML and emitted
CSV are parsed and compared. Empty comparisons return explicit 404 CSV;
unknown/unavailable selection returns 400. Unexpected malformed-input errors
retain the existing diagnostic boundary. No source scenario is repaired or
silently replaced by baseline data.

## User workflow and limits

Chromium exercised unchecked defaults, applying two choices, reload, CSV
download, year changes, AM/month filtering, extraneous round trip, 390px layout,
and clearing selections with no page errors. Screenshots are retained beside
this review. Shared report CSS and CSV client were used; authentication, NoDb
loading, and shared shell were isolated for this local fixture smoke.

This approves local implementation correctness. Production identity/auth/full
shell validation and deployment are not claimed. Final gate results are in
`20261010_validation.md`; broad-suite completion is tracked separately.

## Artifact discovery correction review

Reviewed against `d89ace269`; approved with no unresolved high/medium findings.
Readonly no longer proves completion. Empty-state artifact-backed children are
valid; selected writable children prepare missing derived tables through the
existing reader. Containment includes source and write targets, cache, shared
climate/CLI inputs; absent optional climate remains valid. Original project data
is untouched by validation. Outlet initialization requires its form.

Regression evidence: 91 focused tests plus two real staging/partial-staging
tests; 933 Jest tests. Actual-project copied output produces 16,437 staged events
and independently verified CSV dates/values. See validation record for limits.
