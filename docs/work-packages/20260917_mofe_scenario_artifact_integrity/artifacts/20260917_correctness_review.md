# Correctness and user-experience review - MOFE scenario artifact integrity

> Code and Forest review PASS; production deployment remains operator-owned.

The compact pre-implementation contract at SHA-256
`aab2b182422f900a5a4d8ce96d09b475bc77bdee3ac904e580e2fecb5361e896`
passed independent correctness review with no unresolved High or Medium contract
finding. Implementation and Forest evidence gates now pass; production repair
remains pending explicit deployment confirmation.

## Metadata

- **Package**: `docs/work-packages/20260917_mofe_scenario_artifact_integrity/`
- **Reviewer**: independent `correctness_review`
- **Date**: 2026-09-18 UTC
- **Scope reviewed**: SBS MOFE build, global class-to-class landuse mutation,
  canopy override propagation, Forest acceptance, and production repair
- **Commit/branch context**: starting revision
  `714693a00c1ce47def86ba0b984065262b9f49bd`; implementation `f4152ac69`
- **Canonical contracts**: accepted
  `docs/schemas/mofe-management-artifact-contract.md` plus contracts named in the
  contract decision artifact; evidence claims follow
  `docs/standards/generated-artifact-validation-standard.md`
- **Related QA/security artifacts**: secondary QA PASS; dedicated security review
  not required under current low-impact scope

## User Outcome

- **User goal**: distinct Rithet Creek fire and thinning selections produce model
  inputs and outputs based on those selections, and the eight affected production
  runs are corrected after validated deployment.
- **Success presented to the user as**: persisted intent, generated combined
  managements, prepared WEPP inputs, and refreshed results agree, with actual
  Forest and wepp1 evidence.
- **Failures that may reach the user**: validation errors for unknown classes or
  incomplete state; explicit generation/job failure for malformed state or writer
  errors; no false completion.
- **Partial-state behavior**: preserve the existing writer and RQ exception
  behavior; this package adds no staging, rollback, or recovery protocol.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Single-OFE; MOFE never used | yes | Preserve existing single-OFE behavior | Existing branch unchanged; related regression suite PASS |
| MOFE state absent before build | conditionally | Build normally or return explicit build-first error for a mutation | Direct absent-state regression PASS |
| MOFE state present but empty | conditionally | No false treatment completion; follow operation contract | Direct empty-state regression PASS |
| Populated MOFE assignments | yes | Generate files from final assignments | Real writer tests and eight Forest runs PASS |
| Supported legacy assignments | yes | Normalize without schema migration | Existing normalizer unchanged; legacy RQ signature regression PASS |
| Malformed/incomplete assignments | no | Bounded explicit failure before completion | Nonsequential/incomplete assignment regressions PASS |
| SBS absent | yes | No burn remap | Direct no-SBS fixtures and Forest baseline PASS |
| SBS classified 130 | yes | Preserve unburned management | Real GDAL/SBS test PASS |
| SBS classified 131/132/133 | yes | Select effective low/moderate/high management once | Real GDAL/SBS test and Forest spatial mix PASS |
| Explicit canopy override absent | yes | Preserve source/RAP behavior | Source-template/RAP regressions PASS |
| Explicit canopy override populated | yes | Apply stored value unless RAP currently supersedes it | Direct 0.30/0.50/RAP tests and Forest thinning PASS |
| Writer working | yes | Remain pending; file existence is not success | Completion-time real file assertion PASS |
| Writer failed | no completed result | Existing exception path; no completion trigger | Real local and Forest failures PASS |
| Writer completed | yes | NoDb, landuse files, and summaries agree; prepared inputs are checked after normal WEPP preparation | All eight full Forest readbacks PASS |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Unknown source or target management class | expected validation error | existing canonical error envelope; no mutation | invalid request |
| MOFE mutation before MOFE assignments exist | expected state error | build-first guidance; no false success | assignment cannot be inferred safely |
| Malformed/incomplete persisted assignments | exceptional project-state error | explicit failure with diagnostics | required generation state is corrupt |
| Management writer failure | exceptional execution error | existing failed job/request; no completion event | do not claim success after an exception |
| Stale superseded RQ job | expected orchestration state | skip without mutation or completion trigger | preserve existing stale-job contract |
| Equal outputs after verified equal effective inputs | valid scientific outcome | explanation in acceptance artifact | outputs must not be forced to differ |

## Review Checks

- [x] Canonical intent is named; implementation and tests are not treated as
      authority for user behavior.
- [x] Absent, empty, populated, supported legacy, and hostile states are tested
      or explicitly ruled out.
- [x] Input combinations and persisted/filesystem states are reviewed separately.
- [x] Direct generated-content tests exercise each of the three changed producer
      paths.
- [x] Mocks do not replace SBS classification or the writer boundary that caused
      the production failure.
- [x] Existing authorization, locking, and containment preserve every valid state.
- [x] Existing failure behavior is preserved without adding recovery machinery.
- [x] Errors and recovery guidance are understandable and actionable.
- [x] Existing workflows remain compatible except for corrected generated bytes.
- [x] Coverage claims name all covered dimensions and direct evidence.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Full SBS MOFE build | Classified severity was translated twice | Real SBS/generated-management regression | Consume classified code once | Resolved in code |
| COR-02 | High | Global class mapping | Persisted assignments changed without regenerating files | Real writer/completion/failure/retry regression | Regenerate before completion | Resolved in code |
| COR-03 | High | Canopy thinning | Stored overrides did not reach MOFE files | Public canopy mutation, prepared-file, summary-retention, RAP tests | Propagate and retain explicit override | Resolved in code |
| COR-04 | High | Validation/release | Prior actual-project job was called fixed without generated-file readback | Eight complete Forest scenarios and retained full readbacks | Make actual Forest content evidence a hard gate | Resolved at Forest gate |

## Verdict

- **Implementation gate**: PASS, independent `correctness_review`, 2026-09-18 UTC.
- **Implementation findings**: COR-01, COR-02, COR-03 resolved by direct artifact
  tests and bounded source correction. No unresolved High/Medium code finding.
- **Forest gate**: PASS, independent `correctness_review`, 2026-09-18 UTC.
- **Release recommendation**: hand off to Roger's deployment gate; no production
  deployment or repair is authorized by this review.
- **Reviewer scope**: source and tests, including public canopy edit, retained
  MOFE overrides, real SBS classification, generated/prepared managements, writer
  failure/retry, absent state, and nonsequential segment IDs. Local tests isolate
  NoDb locking and unrelated slope/soil preparation; they do not prove deployed
  workflow equivalence. The separate live review verifies eight 15/15 job trees,
  3,640 hillslopes, 8,520 segments, all 14,576 retained live input-file hashes,
  expected covers/classes, recomputed summary distributions/totals, download
  hashes, real writer failure without completion, identical retry/restored
  manifests, all 7,897 restored hashes, and preserved failed-archive diagnostics.
  Five deployed service hashes and 1000:993 worker identity match the candidate.
  No unresolved High/Medium findings remain. The documented class-200 and SBS
  scientific caveats remain interpretation limits, not artifact mismatches.

## Artifact Observability Gate

- [x] Comparable project layout and canonical artifact inventory are named in the
      canonical contract.
- [x] Existing inputs and generated outputs remain visible through the normal
      project boundary.
- [x] Real writer/failure tests and Forest evidence inspect generated content.
- [x] No new hidden storage or artifact boundary is introduced.
