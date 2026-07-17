# Independent Post-Fix Review A

Verdict: **No — not closure-ready.**

No high findings remain. Two medium and two low findings require disposition.

## Medium findings

### M1 — `batch_runner.js` lacks one producer owner

Evidence:

- `child_package_register.md:200` assigns `batch_runner.js` to
  `SURF-02A/02B`.
- `controller_audit_register.md:121` repeats `SURF-02A/02B` as its owner.

This violates the required once-only producer ownership for all 56 bundled
modules.

Required disposition: assign one primary producer owner, likely SURF-02A, and
identify SURF-02B as a consumer or execution facet.

### M2 — Stateful ERMiT export is absent from the exact ledger

Evidence:

- `templates/reports/ermit_export_download.htm:1` directly extends
  `base_pure.htm`.
- Lines 124–125 POST for an RQ session token.
- Line 220 POSTs the export submission.
- The page polls job status and performs an authenticated download.
- `controller_audit_register.md:144` and `child_package_register.md:188` only
  classify the generic report-shell package as low-risk and read-only.
- The generic domain-report parenting statement at
  `child_package_register.md:223` does not capture this template’s
  authentication, queue, and download contract.

Required disposition: give this template an exact high-security owner,
route/RQ/test mapping, and bounded package. If a new execution unit is
necessary, update the 67-unit total.

## Low findings

### L1 — Location-form hosts are not exact in the coverage ledger

SURF-01 mentions location forms, but the exact host row omits:

- `templates/locations/portland/index.htm`
- `templates/locations/seattle/index.htm`
- `templates/locations/spu/index.htm`

Required disposition: list these production CAP/form hosts explicitly.

### L2 — Initial Review A severity count is inaccurate

`tracker.md:84` records the initial review as two high, two medium, and one low
finding. The verbatim initial review contained three high, two medium, and one
low.

Required disposition: correct the count before preserving the raw review
artifact.

## Verified

- Production bootstrap: exactly 33 source keys and 33 ledger keys, each with one
  primary package owner.
- Arithmetic: exactly 67 units — 3 GOV, 39 DOM, 9 SHR, and 16 SURF.
- Builder: exactly 56 unique bundled modules; all are allocated, although
  `batch_runner.js` ownership remains non-unique.
- `selection_utils.js` now has one producer owner and explicit consumers.
- Authentication, profile/session, and root-user-management surfaces are
  included.
- The Batch Runner durability dependency now uses its exact package path.
- The formerly oversized packages were split and now have explicit 1–4-week
  estimates plus mandatory first-day boundary probes.
- DOM-01 now explicitly depends on SHR-01 through SHR-04B.
- `git diff --check` passes.

## Initial Review A findings, verbatim summary

- **H1:** The coverage ledger was an unpopulated scaffold.
- **H2:** Authentication, profile/session, and root user-management Pure
  surfaces were missing.
- **H3:** Map, Landuse, Climate, AgFields, WEPP/SWAT, shared foundations, and
  Batch Runner contained knowingly oversized boundaries.
- **M1:** The claimed 33-entry once-only package assignment was false because
  primary and facet ownership were conflated.
- **M2:** `selection_utils.js` ownership was contradictory.
- **L1:** The Batch Runner durability dependency was unnamed.

Disposition status:

- H1 resolved structurally.
- H2’s named omissions resolved, but the newly identified ERMiT gap remains.
- H3 resolved.
- M1 resolved.
- M2’s `selection_utils.js` issue resolved, but once-only bundled producer
  ownership still fails for `batch_runner.js`.
- L1 resolved.

No files were edited.
