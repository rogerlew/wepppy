# Correctness and User-Experience Review - Post-fire likelihood report

## Metadata

- **Package**: `docs/work-packages/20260915_postfire_debris_flow_report_implementation/`.
- **Reviewer**: `/root/report_contract_review`, independent reviewer role.
- **Date**: 2026-09-16 UTC.
- **Scope reviewed**: validated table projection, accepted-assessment reader,
  Flask page/query/detail/attachment routes and registration, Pure template,
  controller, existing-control link, passive Unitizer bootstrap correction,
  focused tests and retained saved-run/browser evidence.
- **Commit/branch context**: current branch; reviewed checkpoint
  `ac4deb681073af8abe87bf631b5380e24fea8a26` precedes implementation changes.
- **Canonical contracts**: [report contract](../../../ui-docs/contracts/postfire-debris-flow-report-contract.md),
  especially Data authority, Fields and interactions, Valid states, and Exact
  read interface; module `docs/rainfall_results.md`, Additive report projection;
  production M1/M3/runtime publication contracts; shared report shell and
  artifact-observability standard.
- **Related reviews**: [checkpoint reviews](contract_reviews.md),
  [runtime disposition](runtime_review_disposition.md),
  [dedicated UX review](20260916_ux_review.md),
  [security review](20260916_security_review.md) and [validation](validation.md).

## User Outcome

- **Goal**: inspect an existing accepted M1/M3 assessment without rerunning it;
  compare rainfall scenarios, 50% equality thresholds and individual storms.
- **Success**: familiar report with the saved model/source, explicit freshness,
  consistent units, unique-event counts and precisely scoped downloads.
- **Reachable failures**: denied access, invalid requests, absent/replaced or
  damaged assessments, unavailable currentness, unavailable scientific rows,
  and transient query/detail failures. None may become a numeric zero.
- **Partial behavior**: retain coherent accepted values and input/terrain
  explanations. Failed replacement does not relabel or erase prior acceptance.
  Replacement disables obsolete exports; transient failure labels retained data
  and offers local Retry. No report action acquires sources or runs a model.

## Valid-State Matrix

Paths below are repository-relative. `reader tests` means
`tests/nodb/mods/test_postfire_debris_flow_report.py`; `route tests` means
`tests/weppcloud/routes/test_postfire_report_bp.py`; `controller tests` means
`wepppy/weppcloud/controllers_js/__tests__/postfire_report.test.js`.

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Optional module absent / never used | Yes | Empty assessment without creating state | Reader `test_absence_does_not_initialize_optional_state`; controller absent-state test |
| Present but zero wet events | Yes | Empty storm list; retain available design/inverse values | Existing results `test_empty_bundle_and_unavailable_null_sort`; controller zero-wet-event test; layered coverage, not a live empty run |
| Saved M1/NOAA populated | Yes | Exact saved values and M1 dNBR assessment identity | [M1 saved verification](m1_saved_validation.json); [M1 browser](browser_m1_verified/browser.json), 9,150 events |
| Saved M3/CLI populated | Yes | Exact saved values and model-attempt assessment identity | [M3 saved verification](m3_saved_validation.json); [M3 browser](browser_m3_verified/browser.json), controlled 30-event validation basin |
| Supported legacy v1 M1 | Yes | Independent support, no invented mask; old catalog callers work | Reader real v1 fixture and `test_reader_retains_tables_and_two_argument_catalog_compatibility` |
| Partial M3 with complete common coverage but unavailable terrain | Yes | Null likelihood with specific terrain explanation; coverage is not confidence | Reader `test_validated_partial_m3_keeps_known_terrain_reason`, two real persisted v2/mask/parquet fixtures; controller full-coverage/missing-terrain test |
| Stale accepted result / newer failed attempt | Yes | Prior model remains identified; notice does not imply new success | Both saved/browser runs are correctly stale; reader currentness/newer-model test |
| Missing, failed or symlinked currentness dependency | Yes for saved inspection | Preserve valid values with unknown currentness; no optional state initialization | Reader missing-dump, currentness-failure and symlinked-dump tests |
| Filters match nothing / invalid date labels | Yes | Distinct empty-filter message; invalid dates do not remove otherwise usable events | Results query tests and controller filter/invalid-date tests |
| Accepted snapshot replaced during read | Exceptional | Explicit replacement/reload, no mixed assessment | Reader acceptance-race test; route replacement test; controller replacement/late-response tests |
| Damaged, unsupported or hostile input | No | Bounded sanitized errors; no unchecked fallback | Real corrupt-table and symlink-swap reader tests; route malformed/repeated/auth/error tests |
| Byte-identical archive restore | Yes | Same accepted values and downloadable content despite changed timestamps | Reader actual copied/restored-file test; canonical `tests/rq/test_project_rq_archive.py::test_postfire_records_survive_canonical_archive_and_restore` |
| Temporary detail/page failure | Expected operational failure | Retain coherent view; nearby Retry recovers first/last-row details and paging | Both browser records include controlled detail failures; M1 also exercises failed paging; controller retry tests |
| Selected event moves off-page after duration reset | Yes | Preserve selection if it still matches filters | Three controller regressions cover retention, genuine exclusion and late detail responses; final M1 browser records `preserved_after_duration_and_paging` |

Input dimensions reviewed separately: M1/M3, CLI/NOAA, 15/30/60 minutes,
v1/v2, simulation/calendar/invalid labels, null/interior/endpoint probabilities,
filters/sort/page/detail/unit/export actions, owner/public/denied access and `pup`
URL context. Coverage is targeted and layered, not an exhaustive Cartesian product.
The currentness failure tests deliberately substitute the optional service
failure; real filesystem validation is not mocked away. The `pup` test verifies
propagation with shared context stubbed; it is not a live child-run authorization test.

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| No accepted assessment | Expected | Normal empty page; query pin becomes 409 replacement | Exact read interface distinguishes initial absence from obsolete query state |
| Missing currentness only | Expected supported degradation | Saved values plus unknown-currentness notice | Accepted bundle authority is independent of current dependency availability |
| Missing/corrupt accepted bundle | Exceptional | Sanitized 409 results unavailable and reload/control guidance | Never substitute unchecked data or zero |
| Invalid parameters / unknown event or artifact | Exceptional request | 400 invalid input / 404 not found | Typed bounded read interface and exact identities |
| Access denied | Exceptional request | Existing 401/403 policy, no result disclosure, no-store | Existing run authorization applies to every endpoint |
| Infrastructure / unexpected error | Exceptional | Sanitized 503 / 500; details remain server-side | Local report error boundary; valid saved values survive currentness-only failure |
| Missing required shell state | Exceptional incomplete project | Readable 503 error and Reload; no state creation | Explicit shell read-only contract and missing-shell route regression |
| Scientific row unavailable | Expected model/data outcome | Reason beside unavailable value; unaffected rows remain usable | Existing scalar/result semantics, not a worker or transport failure |
| Query/detail transport failure | Expected operational failure | Coherent previous view and scoped retry; previous-view CSV labeled | Report valid-state and export contracts; controlled browser recovery |

## Review Checks

- [x] Canonical intent and checkpoint are named separately from implementation evidence.
- [x] Absent, empty, populated, legacy and hostile states are covered as listed;
  unsupported claims of exhaustive coverage are not made.
- [x] Input combinations and stored/runtime states are separate dimensions.
- [x] Real temporary files exercise changed hash, mask, descriptor, restore and
  optional-state boundaries; authorization tests retain the real shared policy.
- [x] Mocks do not replace the changed filesystem/provenance validator.
- [x] Valid legacy/partial/restored states remain usable under containment checks;
  no minimum coverage rejection was added.
- [x] Partial success, currentness, retry and descriptor cleanup are explicit.
- [x] Known terrain reasons and local detail/page recovery are understandable.
- [x] COR-R03 selection compatibility is closed and independently rechecked.
- [x] Real rendered default-versus-postfire bootstrap regression preserves
  existing reports and explicit Unitizer actions; final focused and browser
  reruns cover the late conformance fixes. Root reports broad gates complete.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-R01 | Medium | Restored artifacts | Original ctime/mtime equality rejected byte-identical restores | `report.py::open_attachment`; actual restore/mutation tests | Pin accepted size/hash and retain within-read descriptor checks | Resolved, independently inspected |
| COR-R02 | Medium | Partial M3 | Known terrain reason was discarded; UI lacked accepted reason mappings | Persisted partial-M3 fixtures and controller missing-terrain test | Preserve safe known codes and plain-language explanations distinct from coverage | Resolved, independently inspected |
| COR-R03 | Medium | Duration/selection | Page reset cleared a still-matching event solely because it was off-page | Three controller regressions and final M1 off-page browser task | Preserve eligible selection using saved duration details without injecting rows or changing pagination | Resolved, independently inspected |
| LIVE-01 | Medium | Initial units/render | Mock concealed use of nonexistent Unitizer precision API | Failed browser artifacts; real-client controller regression | Use public category-unit precision | Resolved; verified browser reports no page errors |
| LIVE-02 | Medium | Passive read | Inherited DOM-ready bootstrap persisted project unit preferences | `browser_m1_final`; real Jinja inheritance test; real UnitizerClient test; final M1/M3 browsers | Suppress only postfire initial persistence, retain existing-report default and explicit user actions | Resolved, independently inspected |

## Verdict

- **Gate status**: `pass`.
- **Unresolved findings**: High 0; Medium 0; Low 0 owned by this review.
- **Release recommendation**: `ship` for the authorized local implementation
  delivery. Production deployment and push remain outside this authorization.
- **Reviewer sign-off**: `/root/report_contract_review`, 2026-09-16 UTC;
  backend and integration findings resolved, final browser evidence inspected.

Final validation reported by the executing agents: 44 focused reader/route/real
Jinja tests; 21 controller tests; frontend lint and 898 tests across 112 suites;
full Python 8,672 passed, 103 skipped, 3,128 warnings in 1,114.47 seconds. The
full Python run began before the final rendered-shell test was added; the final
focused run covers that addition. This reviewer inspected code, regressions and
retained browser/saved-result evidence rather than rerunning the broad suites.

Final verified browser records finish at 04:05:29 UTC for M1 and 04:05:20 UTC
for M3, with no project-mutation requests or page errors. M1 protects 18 files,
M3 protects 23; separate saved-bundle validation protects 23/28 files and compares
every saved result family and attachment. These inventories differ intentionally;
do not combine their counts. Existing recorder requests are identified separately,
not relabeled as zero HTTP writes. Residual coverage limits are the layered
matrix above, no live child-run authorization case, and no human usability study.
The UX review's optional low-priority muted-help polish is not a correctness
blocker; no additional runtime redesign is recommended.

## Artifact Observability Gate (Required)

- [x] Existing postfire production module and Geneva/report shell are the named
  precedents. Fixed results remain events/design/inverse parquet, manifest and
  v2 validity mask; visible attempts retain existing source/failure records.
- [x] No project writer, hidden storage or archive exclusion was added. Normal
  authorized browsing remains available alongside fixed report downloads.
- [x] Existing real writer/failure tests retain records; canonical archive test
  proves member coverage and byte equality. New restored-reader regression
  protects inspection/download. Both live browser records verify ordinary browse
  and fixed downloads; saved verification checks exact content hashes.
- [x] No observability exception is requested. Failed/intermediate browser
  evidence remains in this visible package rather than being overwritten.
