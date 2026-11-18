# Unrutted partial-crossing tracker

**Updated:** 2026-11-17 UTC
**Status:** RUPC-01/RUPC-02 deployed to forest test server; requested RQ run verified. No wepp1 rollout or site calibration.
**Branch:** `work/roads-unrutted-strip-contract`
**Worktree:** `/tmp/wepppy-roads-unrutted-strip-contract`
**Contract ancestor:** `8e87b236301364c4b743fd7bec87b7640b35cd46`

## Task board

- [x] Capture scope, rationale, incident and implementation-scoped test boundary.
- [x] Resolve formula, feasibility, existing limits and compatibility.
- [x] Amend current contracts and ADR-0146; record exact operator ratification.
- [x] Obtain two independent contract reviews and commit checkpoint before code.
- [x] Implement preparation, canonical crossings, native geometry and accounting.
- [x] Preserve current-result lifecycle and shared-source map/detail association.
- [x] Run scoped regressions and native forest acceptance slices/control.
- [x] Close correctness/security findings and update user/operator/developer docs.

## Decisions and rationale

2026-11-17 UTC — Roger selected an intentionally simplified strip abstraction,
replacement of 60%, conserved total hillslope area and road area where feasible.
Flowpath walking and switchback connectivity are explicitly deferred.

Roger limited tests to implementation changes and authorized mutation/forking of
the synced forest run. He explicitly approved physical-width road OFEs at 4%,
overlap-based strip widths, proportional compression with visible road-area loss,
and retained 10 m minimum/three-crossing cap: “i approve. proceed with implementation”.
The reviewed contract was committed before implementation.

Independent review found segmentation dependence, emitted-area precision gaps,
zero-contributor contract conflict, expensive geometry grouping, and missing
secondary-source display associations. All are dispositioned in review artifacts;
no medium/high findings remain. No new dependency or infrastructure is shipped.

## Validation receipts

- `artifacts/20261117_scoped_tests.log`: 191 passed, two existing dependency
  deprecation warnings. Seven affected test modules; no full repository suite.
- `artifacts/20261117_native_evidence.json`: fresh 141/42 slice execution, native
  input hashes and area closure, replacement PASS closure receipts, exact watershed
  consumer hash, 5,844 daily report rows, current detachment reader, retained
  byte-equal native geometry and unchanged source upload/baseline hashes.
- Runtime: existing forest image, uid 1000/gid 993/groups [993], umask 0022;
  isolated validation service mounts candidate checkout without remounting app.
- No-road control: original baseline parameters, two half-width profiles; total
  runoff differs by roughly 5–6 parts per million. Diagnostic only.
- Broad-exception changed-file enforcement passes (net -1). Markdown/ADR checks pass.

## Known limitations and retained failures

Validation run: `/wc1/runs/ru/rupc-misty-validation`.
Source: `/wc1/runs/mi/misty-eyed-divorcee`, unchanged.
The validation copy uses explicit synthetic fill/buffer values from an existing
fixture (30 m, 10%); these are not measured site data or new runtime defaults.

The complete copied upload fails eight profiles for non-positive upstream OFE
lengths. Some distance-to-channel medians exceed abstract hillslope lengths.
This is the approved explicit failure policy, not silently corrected placement.
The successful acceptance uses selected valid partial-crossing slices on 141 and
42. It must not be reported as the entire site repaired or scientifically calibrated.
Native WAT/PASS serialization reconciliation remains visible and follows existing
accounting; planned/emitted slope geometry closes to the approved absolute bound.

## Handoff and completion states

Implementation and scoped forest validation complete. Integration, publication,
wepp1 deployment and full-site repair have not occurred. Preserve the validation
copy and evidence. Future full-site use needs defensible fill/buffer inputs and
an explicit decision about infeasible profile placement; do not silently clamp it.

Documentation tooling note: installed wctl doc wrappers use the shared checkout;
validate this worktree via explicit `--project-dir` or direct `markdown-doc`.

## RUPC-02 amendment tracking

Starting implementation: `e6989a622f7aea86126d098f48e2e57c15f35b61` on the same branch.
The operator requested top placement and authorized contract amendments. This
supersedes the earlier requirement to reject every non-positive upstream profile;
it does not erase the retained eight-failure evidence.

- [x] Draft canonical placement, role ordering, area and lifecycle amendments; update ADR.
- [x] Complete two independent contract reviews; standalone checkpoint committed.
- [x] Implement adjusted layouts, provenance and execution-policy admission.
- [x] Run 199 scoped tests and native full-upload retries with all eight prior failures dispositioned.
- [x] Complete fresh correctness/security reviews and user/operator documentation.

The operator subsequently approved implementation. RUPC-02 is now locally
complete; synthetic fill/buffer values remain validation fixtures, not site calibration.

RUPC-02 standalone contract checkpoint: `f46d59422009d5adb8641b1d2b7494cd5f9b788a`.
Both reviews pass; no RUPC-02 implementation edits precede this ancestor.

### RUPC-02 validation and remaining limits

- `artifacts/20261117_top_placement_scoped_tests.log`: 199 passed, two existing
  dependency deprecation warnings; six affected modules, no full repository suite.
- `artifacts/20261117_top_placement_native_evidence.json`: exact native input hashes,
  area readback, 24-profile full-upload run with synthetic 5 m fill, replacement
  receipts and watershed consumer inputs, 5,844 daily report rows, inspection
  disclosure, unchanged original source, and all eight prior failures dispositioned.
- Native exact fit (24.3 m hill, 4.1 m road, 20.2 m fill) emits road/fill only;
  25.3 m hill adds 1 m downhill landuse. Each produces 5,844 parsed daily PASS rows.
- Original synthetic 30 m fill run: crossings on 42, 82 and 141 now execute with
  top placement. Hills 43, 62, 63 and two crossings on 143 still fail because
  4 m road + 30 m fill exceeds their approximately 25–30 m hillslope lengths.
- Correctness review closed decimal exact-fit and failure-provenance findings.
  Security review closed historical-restore validation and marker/design bypasses.
  See `artifacts/20261117_top_placement_reviews.md`; no medium/high findings remain.
- Broad-exception enforcement passes, net zero new catches. Documentation and ADR
  checks pass. Code-quality telemetry is observe-only; radon was unavailable.

Retained copies: `/wc1/runs/ru/rupc2-misty-validation` (30 m fill, five expected
failures), `/wc1/runs/ru/rupc2-misty-shortfill` (5 m fill, completed watershed), and
`/wc1/runs/ru/rupc2-native-shapes-accepted` (native exact/short shapes). No source
project mutation, production deployment, or claim that the 5 m fill is correct
for Marta's roads. Top placement explicitly assumes no runoff from land above.

End-user documentation audit: corrected the design-table layout, the short-downhill
exception for top placement, and stale positive-upslope troubleshooting guidance.
Verified the top-placement limitation, road/fill fit error and rerun instructions;
scoped Markdown lint passes. Documentation only; no runtime changes.

## Forest test-server rollout and requested run — 2026-11-17

Operator requested deployment to forest and an RQ run of `misty-eyed-divorcee`,
with the GeoJSON completed. Forest bind-mounts `/workdir/wepppy`. Fast-forwarded
the shared checkout from `e4eafdd3e` to reviewed `9757f38db`, preserving unrelated
tracked/untracked work (targeted PROJECT_TRACKER stash restored successfully).
Reused 199 passing scoped tests; no image rebuild or full suite. Affected queues
were empty; acquired/resumed the existing owned RQ deployment fence around targeted
Compose restarts. Web, RQ engine/workers, browse, query-engine and download came up;
source hashes match the reviewed checkout. No production deployment script used.

The operator clarified this is the test server. Selected the successful provisional
fixture values, disclosed before mutation: 5 m fill and 30 m buffer at 10% grades.
Materialized existing 4 m width, loam and 20% rock defaults. These are test assumptions,
not measured site values or newly changed runtime defaults. All 55 feature geometries
and prior properties were preserved. Backed up original GeoJSON/NoDb and baseline
hashes under `roads/forest_rollout_20261117/`, then used the guarded Roads upload setter.

Preparation job `e04ed015-51dc-4206-a6be-cc4fc29a3d2a` finished at 18:57:23 UTC:
55 input features, 7 prepared segments, zero elevation splits/mapping warnings.
Run job `829ce9de-885d-44bc-8f38-0262cfed7657` finished at 18:59:23 UTC:
15 road + 9 remainder profiles and completed watershed/report generation.
Readback at 19:00:14 UTC verifies exact native input hashes, 1e-6 m² area closure,
replacement PASS closure/no baseline double count, canonical watershed consumers,
5,844 daily report rows, current-result admission, inspection disclosure and unchanged
baseline WEPP files. Source GeoJSON changed intentionally; baseline files did not.

Receipt: `artifacts/20261117_forest_rq_rollout.json`; detailed immutable attempt
readback and original input backup remain under the run's rollout folder. No remote
Git integration/publication or wepp1 rollout is claimed. Operator metadata friction:
Roads schema/default catalogs return 404 despite live OpenAPI/pipeline registration;
register those existing operations in the metadata catalog as a separate small fix.
