# Execute Roads modeled-area accounting repair


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes &
Retrospective alongside the package tracker. This is the completed plan for the
operator's native/WEPPpy Roads repair; unrelated active packages are independent.

## Purpose / Big Picture


Correct Roads report-input mismatch and duplicated modeled area using complete
MOFE footprints. MOFE means a modeled hillslope profile containing multiple
ordered overland-flow elements. Keep all contributor MOFEs; reduce baseline
response to remaining modeled area and expand the target area when necessary.
Use identical represented-area decisions in canonical PASS before routing and
in water aggregation. Prove fresh routed and report results on isolated UM1.
Geographic overlap is explicitly unnecessary under the latest operator direction.

## Progress


- [x] (2026-10-22 UTC) Reproduce missing baseline WAT, wrong denominator and duplicate PASS.
- [x] (2026-10-22 UTC) Obtain scope and task-scoped commit authority in both repositories.
- [x] (2026-10-22 UTC) Record modeled-MOFE direction, superseding geographic partition.
- [x] (2026-10-22 UTC) Draft contract, ADR and cross-contract amendments.
- [x] (2026-10-22 UTC) Obtain both independent approvals; no open high/medium findings.
- [x] (2026-10-22 UTC) Commit approved checkpoint as `83f7410e8`.
- [x] (2026-10-22 UTC) Implement/test native Roads weighted PASS and source-aware water products.
- [x] (2026-10-22 UTC) Build native release and integrate WEPPpy composition/report/cache paths.
- [x] (2026-10-22 UTC) Validate fresh scratch watershed execution and complete report evidence.
- [x] (2026-10-22 UTC) Complete independent correctness/security reviews and 105 focused tests.
- [x] (2026-10-22 UTC) Finish broad-suite run and corrected-browser-path remainder; record limitations and commit integration as `cf3043781`.
- [x] (2026-10-22 UTC) Close local implementation package; no deployment or in-place repair.

## Surprises & Discoveries


Current summary is persisted after regeneration, so pass the current ledger
explicitly rather than reading stale last_run_summary. Raw baseline WAT can be
cleaned up while interchange survives. Existing weighted native PASS is owned
infrastructure but has AgFields-specific strict particle-diameter validation;
UM1 valid road/baseline diameters differ, requiring bounded Roads compatibility.

Equivalent one-OFE reporting water cannot replace raw source aggregation for
TotalWatSed: physical terminal Q differs from its all-OFE Q diagnostic, and
optional SOIL/ELEMENT observations have independent support areas. Preserve both
by aggregating original weighted sources for totalwatsed and publishing a separate
derived WAT for average hillslope reporting.

The geographic audit found outside roads and unlocated rutted buffers. Roger
explicitly removed geographic allocation as a requirement, resolving that design
blocker without inventing positions. Retain the audit as historical evidence only.

The actual report regeneration path must preserve already-hashed source WAT,
SOIL and ELEMENT products; reconverting them changes provenance even when numeric
values match. Corrected regeneration converts canonical PASS only. Source/output
alias and allocation tampering checks were strengthened through independent review.

## Decision Log


2026-10-22 UTC / Roger: Author contract and implement native/WEPPpy integration;
task-scoped commits and PASS reconstruction/fresh routing are authorized.

2026-10-22 UTC / Roger: Keep complete modeled MOFE footprint areas; geographic
overlap is not needed. Use modeled-area response mixing with expansion. For a
point-source target with baseline A and contributor total C, baseline remainder
B=max(A-C,0), modeled target T=B+C. All road sources retain full area. Existing
replacement targets use full strips+remainder, exclude baseline and supersede
additive sources. This is model-space allocation, not geographic closure.

Area authority: stationary WAT OFE sums for continuous runs; native PASS headers
for single storms. Native PASS scales by represented/PASS area, native WAT by
represented/WAT area. Record reconciliation and expansion. No arbitrary tolerance
or new spatial fallback. Final policy is in the canonical contract and ADR-0102.

## Outcomes & Retrospective


Contract checkpoint `83f7410e8` and native implementation `c941cb6` are committed.
WEPPpy integration and full-record isolated UM1 routing/report validation pass.
Native Rust 127 tests, independent native Python 61 tests and focused WEPPpy
105 tests pass. Both independent final reviews pass. Archive/restore preserves
176 lineage files. Original UM1 remains unchanged. Integration is committed as
`cf3043781`. Broad run: 10,883 passed/126 skipped, then an unrelated browser-path
failure; all 183 remainder tests pass with the installed browser path. Existing
OutputScope stubtest alias limitation remains. Package closed for local
implementation and segmented validation; see the execution-validation artifact
for production/rebuild follow-ups and exact limits.

## Context and Orientation


WEPPpy is `/workdir/wepppy`; native is `/workdir/wepppyo3`. No new branches.
Retained incident root is `/wc1/runs/cl/clogging-starch`. Baseline is wepp/output,
Roads is wepp/roads/output. H.wat carries local OFE water/area; H.pass carries
hillslope export. Canonical target PASS already contains combined road deliveries;
standalone contributor PASS must never be counted again in aggregate reports.

Read canonical `docs/schemas/roads-water-accounting-contract.md`, ADR-0102,
output-scope and hillslope-water contracts, and nearest AGENTS before edits.
Roads orchestration is `wepppy/nodb/mods/roads/roads.py`. Native source is
`wepp_interchange/src/hill_pass_combine.rs` and `totalwatsed.rs` in wepppyo3;
bindings are `src/lib.rs`. Python wrapper is
`wepppy/wepp/interchange/totalwatsed3.py`; average report is
`wepppy/wepp/reports/hillslope_watbal.py`. Existing cache provenance machinery
must fingerprint the new accounting source instead of relying on timestamps.

## Plan of Work


Milestone 1 finishes the contract checkpoint. Complete two independent read-only
reviews of current modeled-area documents, disposition all medium/high findings,
and commit canonical amendments, ADR and checkpoint artifacts as a standalone
ancestor. Commit authority is already granted. Record the revision in tracker.
No geographic algorithm or new footprint-input field is required.

Milestone 2 implements native kernels. Extend the owned weighted PASS combiner
with explicit Roads strategy and established Roads first-header particle semantics;
preserve AgFields strict validation. Use originals, scale extensive values and
recompute derived/header quantities, then reparse serialized output. Provide bounded
native source-geometry discovery and weighted water aggregation. Each native
profile retains topology until physical Q/terminal lateral selection. Totalwatsed
uses original weighted profiles and existing optional support-area joins; publish
marked H.accounting.wat.parquet for equivalent canonical-target average reporting.
Use existing Arrow/Parquet primitives without Python numerical fallback or new
dependencies. Cover saturation, expansion, replacement and invalid states.

Milestone 3 wires WEPPpy. Build and persist an explicit modeled-area ledger from
translator IDs, completed manifest roles and native source areas. Preserve
replacement precedence and intentional-skip versus failed-run behavior. Compose
canonical PASS before watershed execution. Generate totalwatsed and marked
accounting WAT from the same ledger, validate readiness/provenance, and bind the
average report cache to accounting-source hashes. Preserve raw archives and raw
consumer semantics. Historical unmarked reports remain historical; no silent
upgrade or regenerated-ready claim without corrected lineage.

Build only affected native crate(s) and atomically refresh canonical py312 files,
recording source revision/dirty inputs, binary hash, API checks and tests. Preserve
unrelated native calendar/HBP work and all unrelated WEPPpy changes. Do not make
an unqualified clean-build claim if unrelated source is included in the build.

Milestone 4 validates end-to-end on a separate UM1 copy. Reconstruct PASS from
original constituent sources, inspect the exact files consumed by the watershed,
run watershed execution, regenerate reports and inspect daily/yearly and average
results. Validate all 5844 days and 16 years, expanded/remainder geometry, volumes,
particle compatibility and original-source hashes. Include multi-OFE replacement,
zero/full occupancy, C>A expansion, zero-road controls and optional partial data
fixtures. Complete focused/broad gates, independent correctness and dedicated
security review. Do not claim production deployment or in-place incident repair.

## Concrete Steps


From `/workdir/wepppy`, run focused `wctl run-pytest` for Roads controller,
interchange and report tests. Follow with `wctl run-pytest tests --maxfail=1`,
API/stub checks if public native bindings change, and scoped `wctl doc-lint`.
Native build/test follows `/workdir/wepppyo3/docs/release-provenance.md` using
Python 3.12 and existing linker settings. Record exact new test and scratch
commands as implemented. Do not auto-start a stopped test stack.

## Validation and Acceptance


A valid contributor-area excess expands modeled area; it is not a negative-area
error. Zero baseline remainder is valid. Complete MOFE footprints and original
native terminal selection survive composition. Canonical PASS is selected once,
reparsed, consumed in fresh routing, and agrees with the water ledger. Old native
baseline and AgFields behavior remains unchanged. Zero-road continuous named
water output matches baseline within floating summation precision.

Malformed sources and missing corrected provenance fail explicitly; legitimate
optional absence remains admitted. Partial optional observations retain their
support weights. Average report Q is physical; TotalWatSed Q diagnostics retain
their existing reduction. Validate cache fingerprints with same-mtime changes,
source alias rejection, file permissions and actual worker-equivalent execution.
No mock replaces the final unmocked artifact/consumer evidence.

## Idempotence and Recovery


Keep originals immutable and use explicit scratch destinations. Rebuild from
original baseline/contributor PASS, never previously combined weighted output.
Native package refresh uses staging plus atomic rename; never truncate a loaded
shared object. Roll back coordinated code/native artifacts together; no production
rollout is included. Keep task commits isolated from unrelated work.

## Artifacts and Notes


Store contract decisions/reviews, source/build receipts, ledger inspection,
prepared PASS and routed/report evidence, tests and final reviews under this
package's artifacts directory. Prior investigation contains exact original symptom
replay. Geographic research is superseded as allocation policy and must not become
an implementation dependency.

## Interfaces and Dependencies


Reuse native weighted PASS and existing streaming water reducers. WEPPpy owns
source selection, ledger persistence, execution and report readiness; native owns
area discovery, numerical weighting, serialization and reduction. New native APIs
are additive; current non-Roads entry points retain their defaults. No new external
dependency, service, endpoint or queue edge.

Revision note: 2026-10-22 — rewritten for Roger's explicit full-MOFE modeled-area
policy. This supersedes geographic and fixed-baseline-area drafts and carries
forward the already-approved implementation/commit/routing scope.

Revision note: 2026-10-22 — implemented and validated native/controller/report paths;
recorded independent approvals, isolated routing and archive evidence.

Closeout note: 2026-10-22 — completed all milestones; retained browser environment,
stubtest and native dirty-source provenance limits without claiming deployment.
