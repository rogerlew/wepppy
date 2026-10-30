# Correctness review: WEPP 261029 promotion

Reviewer: Codex /root, 2026-10-30 UTC, release integration review. Independent
model science/software/disclosure reviews are separately retained alongside this
file. Source631aed1d1c89ed8fa76c5dc3f2e4258a8f199504 on the native default branch.
Authority: docs/schemas/wepp-executable-selection-contract.md (release declarations
and existing projects), docs/binary-lifecycle.md (gates), ADR-0112 and native
physical-water-routing-contract.md (updated-stock ET and source-time attribution).

## User outcome and failure-class scope

Users can explicitly select the matched Linux release and read the illustrated
report. No default or saved selection changes. Invalid sidecar hashes, incompatible
capabilities and unknown IDs remain explicit failures under existing contracts.
The model still rejects genuinely unfunded hourly withdrawals. No fallback binary
or soil tuning conceals failures. Daily/hourly local-input arithmetic, shared
EVAPPM stock and root integration, and fixed-width peak serialization are covered
by native probes and actual generated outputs. The daily negative-exchange and
wider channel coupling/clipping limits remain open; Windows is excluded.

## Valid-state and artifact evidence

| State or stage | Required behavior | Evidence | Result |
| --- | --- | --- | --- |
| Old saved project | New release selectable; config/manifest unchanged | postvendor-targeted.log, parameterized save/reload test including261029 | pass |
| Existing default/legacy choice | Preserve stored executable; no automatic upgrade | selection policy tests, unchanged production configuration | pass |
| Absent/malformed/hostile declarations or ID | Unknown support or explicit rejection; no silent substitution |20 capability tests and policy cases | pass |
| New matched pair | Correct role resolution and declared MOFE/upload support | selected-release-runtime.json; sidecars/hash checks | pass |
| Prepared inputs | Exact committed fixture bytes consumed in runtime container | fixture manifest and SHA256 in script/receipt | pass |
| Fresh execution |16 years,3OFEs,17532 complete finite/nonnegative WAT rows | actual run_hillslope with runner identity log | pass |
| Consumer boundary |3237 ELEMENT event and17532 WAT daily rows; known absent optional storage stays null | actual Rust interchange/Parquet readback | pass |
| User documentation | Download approved bytes and retain prior release navigation | report-download-check.json | pass |

The direct native failure boundary is exercised by the committed fixture, signed
allocation/guard probes and exact-binary traces. Cedar is supplementary actual
watershed evidence:864 independently regenerated hillslopes and24 watershed years.
No mocks replace the selected-release runner or Rust reader. New project schema,
archive format or visibility behavior is not introduced; normal run artifacts
remain under the existing output inventory and project authorization. Runtime
evidence is retained in scratch, with immutable small receipts in this package.

## Findings and verdict

No unresolved release blocker. Scientific daily-negative-FIN wording and historical
source-label findings are closed. Verification harness findings were corrected
against actual producer/reader contracts without modifying generated outputs:
ELEMENT is event-only; optional absent InterceptionStorage is null. The first
HTTP attempt missed Caddy's configured host and returned empty200; hash/size
checks rejected it before the correct host route passed.

Integration gate: pass. Highest claim: implemented and locally environment-validated
through actual selection, execution, consumer and served documentation. Full
repository sweep and commit/push remain tracked separately. No production
deployment, affected-project rerun, Windows promotion or field validation claim.
