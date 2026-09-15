# Correctness and User-Experience Review - Staley M3 Integration

## Metadata

- Package: `docs/work-packages/20260914_staley_m3_integration/`.
- Reviewer: independent `source_contract_review`, 2026-09-14 local time.
- Scope: recorded-depth policy, original-source snapshots/acquisition/replay,
  generic preparation and owner-bound activation, M1/M3 exact support/results,
  finalization/publication, accepted downloads and control behavior.
- Commit context: production checkpoint `b998d44e2126889e8014cc83230d51f6b89e9c82`,
  plus the reviewed additive `partial_reason` correction in the working tree.
- Canonical intent: module `docs/production_m3_runtime.md`, sections Prepared
  source boundary, Soil policy and stable snapshots, Predictors and exact
  support, Artifacts and publication, State and compatibility evidence;
  `docs/m3_terrain.md`, Accepted engineering definition and Owned implementation
  and input contract; ADR-0067; UI contract
  `docs/ui-docs/contracts/postfire-debris-flow-control-contract.md`, Run action
  and completion, Reload/access/accessibility, Scientific integration amendment.
- Related evidence: [checkpoint reviews](20260914_checkpoint_reviews.md),
  [implementation reviews](20260914_implementation_reviews.md),
  [generic preparation review](20260914_generic_implementation_review.md),
  [network/replay review](20260914_network_reader_review.md),
  [independent builder QA](soil_builder_regression_review.md),
  [security review](20260914_security_review.md).

## User Outcome

- Goal: run M1 or M3 from an eligible project with auditable inputs, exact
  spatial support and downloadable outputs, without rebuilding or changing
  existing soil/RUSLE/WEPP inputs. M3 does not require dNBR or K.
- Success: existing run control/RQ lifecycle, completion time, explicit model,
  Valid coverage/counts, exact downloadable mask and four established result
  files. No report/chart or extra orchestration control is introduced.
- Expected scientific limitations remain successful partial results with null
  unavailable probabilities, retained diagnostics and an explanatory message.
  Missing mandatory project prerequisites disable execution with existing guidance.
- Malformed inputs, changing authority/sources and execution failures do not
  replace accepted results. Visible failed attempts survive; previous outputs
  remain available and retry uses the established run action.

## Valid-State Matrix

This is the reviewed bounded state set, not every possible state/input product.
Test paths below are under `tests/nodb/mods/` unless specified otherwise.

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Feature never used / absent module state | Yes | Read does not create NoDb; no accepted files invented | `test_postfire_debris_flow_production.py::test_absent_read_does_not_create_nodb`; publication absent/empty no-op test |
| Absent or contract-defined empty optional source metadata; schema-valid empty source tables | Yes | Fallback-only or explicit unavailable thickness; never create/refresh upstream cache | Source-preparation fallback-only test; production-soil cellwise/absent tests; real missing-source runtime case |
| Verified primary/fallback source inventory | Yes | Original MUKEY provenance, primary then original THICK fallback, retained identities | Mixed nonuniform M3 composition, two-basin preparation/runtime tests, live large-basin primary/fallback counts |
| Zero/disjoint common support | Yes | Null unavailable predictors/probabilities, exact zero mask; M3 terrain support remains independent | M1 common-support tests; 13 M3 composition cases; missing-source real runtime |
| Full F/S support but incomplete upstream terrain | Yes | T and every dependent probability unavailable; explain why 100% coverage is insufficient | Large-basin live M3 result; COR-UX-01 below |
| Legacy version-1 M1 predictors/results without coverage/mask | Yes | Read/download unchanged, coverage explicitly not recorded; no reuse for new common-support execution | Legacy model-identity reader test, legacy publication/production and controller tests |
| Read-only/ineligible project or wrong DEM/grid/source | View is valid; mutation is not | Preserve authorization; do not enqueue/accept invalid execution | Route tests, real-owner wrong-mask/eligibility finalizer reproductions |
| Populated malformed metadata, corrupt/zero-byte DB, hostile paths or conflicting stable IDs | No | Explicit bounded failure and retained evidence; not mistaken for optional absence | Production-soil corrupt/symlink/metadata/duplicate tests and independent reproductions |
| Source/WAL/authority changes during work | No longer current | Refuse stale acceptance, preserve old pointer and source writer | Real committed-WAL and Ron module-removal regressions |
| Writer failure, interrupted publication, retry | Yes | Previous accepted result survives; retain partial work; explicit publication repair/retry | Real native runtime success/failure/retry, publication filesystem failure/repair tests |

Input dimensions reviewed separately: model M1/M3; CLI/available NOAA design
rainfall; primary-only/fallback-only/mixed/no sources; valid/unavailable M3 T;
full/partial/disjoint/zero SBS-soil support; 100/300 cm thickness; independent
project grids/keys; original and changed source identities. The suite does not
claim the full Cartesian product, all soil surveys or all climates.

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Optional source absent/empty | Expected | Partial unavailable result or fallback, not automatic soil rebuild | Recorded-depth/prepared-source contract |
| Terrain truncated or basin support inconsistent | Expected scientific limitation | Null T/dependent results; bounded terrain explanation | Full-upstream terrain cannot be repaired by reducing soil/SBS support |
| Zero spatial support or unavailable rainfall samples/design estimate | Expected | Partial completion with corresponding bounded reason; downloads retained | Shared support and rainfall contracts |
| Malformed/unsafe populated input | Exceptional | Explicit failed attempt with retained technical details | Do not silently treat corruption as absence |
| Inputs or eligibility change before acceptance | Expected concurrency refusal | Inputs-changed/stale result guidance; prior acceptance retained | Locked finalization authority contract |
| Result/publication I/O failure | Exceptional | Failed/retryable attempt or explicit publication repair; previous outputs retained | Existing NoDb/publication contract |

New `partial_reason` text is selected from fixed messages, not source-provided
metadata. It travels with the accepted record and is rendered through
`textContent`. Legacy records lacking that additive field retain prior messages.

## Scientific/Input Limitations, Not Correctness Defects

- `recorded_depth_v1` is the ratified recorded-endpoint policy, not WEPP horizon
  validity or a new survey measurement. H/Cr admission, R exclusion, bounded
  legacy pairs, weight handling and THICK conversion remain exactly as approved.
- Collection labels from current SDA do not establish historical cached survey
  versions. Offline recovery proves retained transcript/native bytes, not new
  remote retrieval or current remote freshness. No runtime reader implicitly
  downloads missing data or refreshes shared caches.
- M3 T uses maximum upstream raw elevation minus raw outlet elevation, divided
  by square root of full upstream area. It is not conditioned DEM relief or
  catchment maximum minus minimum. The accepted terrain method and scientific
  preprocessing limitations are preserved, not waived for a convenient result.
- `addicted-reservist` has 4,311,420 cells and 1,123 basin cells on the outer DEM
  edge. Native coverage marks terrain potentially truncated. Its T is correctly
  unavailable even though F/S support is 100%; positive probability acceptance
  comes from the separate analytical basin, not this incomplete terrain.
- Both the large real basin and tiny analytical basin lie outside the published
  study-size screen. SI/English warnings remain visible and nonblocking. The
  positive fixture proves execution/arithmetic, not empirical predictive skill.
- Original THICK is a coarse fallback, not newly acquired detailed SSURGO.
  Partial-support estimates describe usable cells, not a fabricated complete
  basin. No minimum coverage threshold or additional rounding gate is invented.
- Generic preparation has distinct-grid/key evidence, not exhaustive geographic
  validation. Bounded admission and separately authorized acquisition remain.

## Independent Live Evidence Readback

Large-project evidence root:
`/wc1/runs/ad/addicted-reservist/postfire_debris_flow/validation/20260914_m3/`.
Positive-M3 evidence root:
`/wc1/runs/pf/pfdf-m3-validation-20260914b/postfire_debris_flow/validation/`.

I independently recomputed every retained event/design probability and inverse
threshold using Table-4 coefficients, checked unavailable rows, and compared
browser-downloaded mask bytes with each result mask. No live mutation was needed.

| Workflow | Verified rows: events / design / inverse | Support | Outcome |
| --- | --- | --- | --- |
| Large-basin M1, `browser_m1` and `m1_numbers.json` | 27,669 / 12 / 3 available | 4,311,306 of 4,311,420; 114 excluded | Arithmetic and exact downloaded mask pass |
| Large-basin M3, `browser_m3_inspect2` and `m3_numbers.json` | 27,669 / 12 / 3 unavailable | 8,705 primary + 4,302,715 fallback; full F/S coverage | Null T/dependent outputs correct; initial UI reason gap identified |
| Positive M3, `browser_m3` and `m3_numbers.json` | 90 / 12 / 3 available | Three primary cells | T = 30/sqrt(300), F = 2/3, S = 100/254; arithmetic/mask pass |

Actual RQ job-info readback shows finished `run_m1_rq` and `run_m3_rq` jobs,
matching attempt IDs and empty child sets. Browser evidence records normal
selection/run/state/status/output requests, finished job attachment, SI/English
warnings, downloads and coverage display. Screenshots were inspected directly.

Final COR-UX-01 live closure: large-project `browser_m3_final2/` records job
`528f1c22-0315-4a49-b164-c5b5f28a90f7` and accepted attempt
`8a6aac78039d4a4fab781e879368372e`. After reload, `completion_message.txt`
contains the normal partial-completion text followed by “Elevation coverage does
not establish complete upstream terrain.” `state.json` carries that exact
`partial_reason`; the accepted manifest still has unavailable T with
`terrain_potentially_truncated`, and coverage remains 100% for F/S. Positive
project `browser_m3_final/` retains `partial: false`, null reason and “Run
complete.” The final large-project PNG is blank and is not claimed as visual
proof of the correction; closure uses the real post-reload browser `innerText`
assertion, accepted/public state, and independent rendering tests.

`protected_before.json` and `protected_after.json` have exactly equal `files`
records for all 22,357 files: `soils.nodb`, `rusle.nodb`, `soils/**`, `rusle/**`
and preexisting `wepp/runs/**`. This reviewer compared the complete retained
inventories, not a fresh third hash of all approximately 13 GB.

`browser_browse2/browser.json` records six ordinary authorized browse/download
200 responses and byte hashes for failed acquisition JSON, native THICK, raw
HTTP body, recovered receipt, copied WAL and an exact predictor mask.
`archive_roundtrip.json` reports canonical archive/restore on an isolated copy:
521 exact restored files, including 111 source-preparation records, 13 HTTP
bodies, 24 SQLite-related files, nine masks, a failed acquisition and two native
THICK files. I reopened the actual ZIP, verified its exact 521-member set and
independently rehashed all 49 source/failure/SQLite/mask-category members in both
ZIP and restored tree. The real archive engine ran; this is not a live-project
restore or an archive-API authorization test.

## Review Checks

- [x] Canonical intent is named independently of implementation/tests.
- [x] Absent, empty, populated, supported legacy and hostile states are
  enumerated, tested or explicitly outside the supported input contract.
- [x] Input/flag and stored/filesystem state dimensions are separated.
- [x] Real SQLite, native rasters, NoDb ownership/finalization, filesystem
  publication and canonical archive boundaries have direct evidence.
- [x] Scientific builders/readers and real persistence boundaries are not
  replaced by mocks; deliberate failure injection is identified as such.
- [x] Noninterference for the enumerated valid states is supported by real
  success/failure/retry tests and retained live upstream inventory equality.
- [x] Partial success, readiness, retry and retention semantics are explicit.
- [x] Partial-completion explanation is confirmed in the corrected live UI
  through post-reload browser text and accepted/public state, with passing
  independent backend/controller tests.
- [x] Existing M1/offline/legacy/download behavior remains compatible except
  for the explicitly ratified common-support production change.
- [x] No exhaustive geographic, source-state or empirical skill claim is made.

## Findings

| ID | Severity | User/state surface | Description / evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Final acceptance after owner change | Original real-Ron module-removal reproduction accepted disabled execution; `_current_authority` now rechecks eligibility/read-only/readiness/snapshot before and within locked acceptance | Preserve refusal and prior pointer | Resolved; independent reproduction now returns `superseded`, no accepted/public result; 59-test runtime/production gate passed |
| COR-02 | Medium | Scientific/source artifact replay | Earlier SQLite sidecars/typed values, equal-count wrong domains, omitted SBS/F proof, source provenance and legacy model dispatch gaps | Exact retained typed sources/support/model and reader checks | Resolved in linked independent implementation reviews and tests |
| COR-UX-01 | Medium | 100% F/S coverage with unavailable M3 T | Original live screenshot only said some probabilities could not be calculated, without the required reason; all probabilities were null | Add fixed accepted/public `partial_reason`, render plaintext, verify corrected live message | Resolved; independent four backend reason tests and 23 controller tests pass; `browser_m3_final2` confirms corrected live post-reload text/state and positive-M3 completion remains unchanged |

## Verdict

- Gate status: **pass**, bounded to the reviewed scientific/source-integrity,
  finalization, user-state/UX and artifact-observability changes.
- Unresolved correctness findings: high 0, medium 0, low 0.
- Release recommendation: **hold package closeout**. Security finding SEC-06
  independently requires owner credential-response confirmation or explicit
  reviewed risk acceptance. Neither a correctness pass nor new code silently
  resolves that external security condition. No deployment approval is given.
- Reviewer sign-off: `source_contract_review`, 2026-09-14; correctness/UX pass,
  package closeout hold for the separate security-response condition.

Parent-reported gates, distinguished from this reviewer's independent runs:
full Python 8,590 passed/103 skipped; strengthened two-grid native runtime 14
passed, including success/result-boundary failure/retry and expanded protected
hashes. The later partial-message delta has independent four-case Python and
23-case Jest results; additional closeout gates belong in the package validation
record. The final full-suite rerun is still in progress at this sign-off and is
not claimed complete. Builder QA is separately signed off and is not substituted
for this review. The parent-reported zero-match scan of 524 text files does not
itself resolve SEC-06 or substitute for owner incident response.

## Artifact Observability Gate

- [x] Comparable module: existing production M1 attempts/publication; canonical
  M3 artifact inventory is in `docs/production_m3_runtime.md`.
- [x] Inputs, intermediate/failed source records, provenance and outputs remain
  visible under normal project browse/download authorization.
- [x] Real writer/failure retention, canonical archive/restore member coverage
  and byte equality, and live browse/download evidence are present as above.
- [x] No hidden/download-only storage or new project archive exclusion is
  accepted. Builder QA's Git exclusions do not hide or remove local records.
- [x] Observability approval is bounded to this evidence; it does not waive
  the external security-response condition or outstanding final test execution.
