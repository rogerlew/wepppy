# Independent correctness review — soil input capacity 23

## Metadata

- Reviewer: Codex independent `reviewer` agent, `/root/correctness_review`.
- Date: 2026-11-19 UTC.
- Candidate: `/workdir/wepppy-soil-input-capacity-23`, branch `feat/soil-input-capacity-23`, base `d228fe0a5`; committed ADR/contracts plus working changes. Native source: `464a5e5e15e1fbcdd4e8232260ecf79ad2645200` against `7d4cf4b5ab24bbc825515d54f25a035062b826bb`.
- Authority: ADR-0150, `docs/schemas/soil-horizon-boundary-contract.md` (“Input capacity and consumption”), `docs/schemas/wepp-executable-selection-contract.md` (“Soil input capacity”).
- Method: read-only source, call-site, test and retained artifact review. Reviewer did not rerun tests or mutate candidate source. Follow-up source verification and retained targeted receipt completed after implementer fixes. Exact reviewed Python source/test hashes are retained in `independent-correctness-scope.json` beside this artifact.

## Findings

| ID | Severity | Surface | Finding and action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Treatments derivatives | `wepppy/nodb/mods/treatments/treatments.py` `_modify_soil` constructed `WeppSoilUtil` with default ten in both SoilSummary and fallback branches before conversion/write. A valid 21-horizon selected-capacity profile therefore failed treatment generation. Forward selected capacity in both branches and exercise real writer/readback. | Resolved; source inspected and real writer regression passed |
| COR-02 | Medium | Location soil derivatives | `wepppy/nodb/mods/locations/location_mixin.py` `modify_soils` constructed utility at default ten. GeneralMod calls this before the already-fixed restrictive-conductivity helper; LakeTahoe also calls it. Forward selected capacity and exercise actual derivative generation. | Resolved; source inspected and real writer regression passed |
| COR-03 | Medium | AgFields Concept 1/hybrid | `wepppy/nodb/mods/ag_fields/concept1_inputs.py` synthesized copied parent soil with default-ten `SoilMultipleOfeSynth`. Both live integrators use a separately selected/inherited compatible executable but did not forward its capacity. Add bounded optional capacity to synthesis, forward AgFields executable capacity from both callers, and test real high-horizon synthesis. Preserve standalone legacy default. | Resolved; source inspected and real writer regression passed |

These were incomplete propagation of the repaired shared assumption, not native physics defects. All were reported promptly and repaired. Both Treatments branches and LocationMixin now receive the selected capacity. AgFields synthesis has an optional default-ten capacity, with the selected AgFields executable capacity supplied by both live integrators. The consumer inventory includes all three.

Closure evidence: `review-consumers.log`, **42 passed**; canonical receipt `.wctl-test-runs/d7fe9f8a044c489fa8451ca927fe1ccf/receipt.json` has `status=passed`, `pytest_exitstatus=0`, `exitstatus=0`. New real Puaulu tests cover both Treatments source branches with 7778/9002, actual LocationMixin conversion/write, and two-OFE AgFields synthesis/readback. Reviewed modifications preserve the standalone legacy limit and choose the AgFields executable independently from the parent executable.

A low-severity documentation gap was also corrected: user-facing soil-file guidance now explains selected capacity and the release ledger records the matched pair. No unresolved documentation finding remains.

## User outcome and failure-class assessment

The user needs generated SSURGO soils with an inserted 200 mm boundary to build and run without losing material. Native input scratch storage is now 23, while calculation arrays and formulas retain `mxnsl=10`. Historical undeclared executables remain limited to ten. No automatic selection migration, horizon merging, conductivity replacement or upload-admission expansion is authorized.

Reviewed raw SSURGO collection and donor serializers; utility conversion/deep-copy behavior; preparation task tuples; Disturbed process dictionaries and MOFE assembly; channel writers; final five runner entry points; executable capability metadata and registry freshness; live derivative consumers. Read-only metadata consumers do not need capacity forwarding because utility construction parses without normalizing. Roads owned one-horizon templates and bounded non-SSURGO dataset serializers retain legacy defaults. Fuzzing, corpus tools and migration utilities are standalone bounded consumers, not silently opted into a new executable.

## Valid-state matrix

| State | Contracted behavior | Evidence reviewed |
| --- | --- | --- |
| Both optional capacity declarations absent | Effective ten; existing selections/defaults retained | `test_capacity_mismatch_and_absence`, capability resolver, no default binary edits |
| Empty/malformed sidecar | Explicit metadata error, no native launch | Existing sidecar schema/identity tests and `_read_release_capabilities` |
| Matching populated declarations 1–23 | Require integer, matching role/source/hash; return separate integer capability | Capacity type/revision tests; real paired release sidecars |
| Legacy generated input 1–10 | Same calculation state and native outputs | 80/80 exact reader states; native original-input paired comparisons; Disturbed parity |
| New 21/22/23 input | Preserve all material records; aggregate using existing formulas | Bounds-checked reader matrix; analytical eleventh/twenty-third material tests; real Puaulu source fixture |
| Existing oversized input switched to old binary | Fail before process invocation without modifying source | Actual-file downgrade check |
| Valid uploaded input | Existing admission remains 1–10; preserve format/topology; capacity validation does not normalize | `validate_soil_text`, preservation tests, validation-only test |
| 24+, invalid count/type or mismatched roles/digest | Explicit failure before serialization publication/native read | Python capacity boundaries and native count 0/24/100 rejection tests |
| Legacy zero-layer water syntax | Serializer preservation retained; not claimed runnable | Retained baseline bounds-checked native failure and candidate explicit rejection |

No claim is made that every native input syntax, dataset or user-state combination is exhaustively tested.

## User-reachable error policy and partial state

Malformed capability metadata, unavailable executable IDs, excess input horizons and inconsistent serialized records fail explicitly under the canonical contracts. Capacity failure occurs before opening a generated destination in the reviewed raw/utility/MOFE writers; tests preserve a prior artifact. Final runner validation reads actual deck soil references without rewriting them. Failed multi-file workflows may retain prior/partial outputs according to existing orchestration; no new transactional rebuild contract is asserted. Native count errors now explicitly fail rather than silently discard surplus horizons.

## Generated artifact evidence chain

| Stage | Evidence | Assessment |
| --- | --- | --- |
| Intent | Accepted ADR/contracts; user-approved nearest CLIGEN station for disposable copy | Supported |
| Persisted selection | Replay receipt records matched final `wepp_261118`; original remains unchanged | Supported |
| Raw generation | Actual RQ build generated 196 raw soils, eight with eleven horizons; real Puaulu writer yields 21 | Supported |
| Prepared input | Replay validates 355 hillslope soils plus 144-OFE channel file; independent Puaulu prep/MOFE test retains 21 | Supported; derivative findings closed by targeted real-writer tests |
| Native execution | All 355 replay hillslopes and watershed completed 100 years; 5,259,456 finite channel rows exactly match 36,524-day calendar | Supported by retained readback |
| Reports/exports | Canonical six post-jobs passed; actual hill/channel/outlet consumers loaded 355/144 rows and finite outlet values | Report-reader and export evidence; no independent browser run |

Evidence root: `/workdir/soil-input-capacity-23-evidence/`. Key files: `native/full-pytest.log` (1824 passed), `native/reader-final.log` (72), `native/state-parity.log` (80 exact), `native/sidecar-tests.log` (14), `release-watershed/report.json` (20 paired executions), `replay-output-readback.json`, and package `artifacts/disturbed-parity.json` (768 identical native outputs).

The original-project replay's selected prepared hillslope profiles are all at most ten horizons; it proves the failing raw build and real workflow, while real Puaulu and native extended-input fixtures prove 21–23 consumption. Development worker image/configuration differs from production; UID/GID/umask and mounted input paths were matched for the disposable workflow. No production activation or original-run repair is established.

## Artifact observability and residual coverage

Existing canonical soil/prepared/output/report paths are retained; no new hidden production-artifact format is introduced. Task evidence also retains raw output hardlinks before configured cleanup. This review does not claim fresh browser/download or archive/restore coverage beyond existing repository behavior. No authentication, queue wiring or output schema changes are proposed by the reviewed capacity implementation. Security review is separate.

Broad Python validation remains in progress at this review checkpoint; derivative repair tests passed. Release remains on hold until required gates pass. Windows release behavior, future sources exceeding 23, and production deployment parity are outside the demonstrated evidence.

## Verdict

Independent correctness code-review gate: **pass**. Unresolved high findings: 0; medium: 0; low: 0. The three identified medium findings are closed by inspected code and retained direct-writer regression evidence. Release recommendation: **hold until required full Python/QA gates pass**. This review does not independently establish deployment readiness or incident recovery. Reviewer sign-off: `/root/correctness_review`, 2026-11-19 UTC.
