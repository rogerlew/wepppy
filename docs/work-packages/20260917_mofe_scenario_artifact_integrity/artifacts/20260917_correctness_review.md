# Correctness and user-experience review - MOFE scenario artifact integrity

> Initial incident findings are recorded here. This is not an approval.

The compact pre-implementation contract at SHA-256
`aab2b182422f900a5a4d8ce96d09b475bc77bdee3ac904e580e2fecb5361e896`
passed independent correctness review with no unresolved High or Medium contract
finding. This artifact's implementation and Forest evidence gates remain open.

## Metadata

- **Package**: `docs/work-packages/20260917_mofe_scenario_artifact_integrity/`
- **Reviewer**: pending independent reviewer
- **Date**: pending
- **Scope reviewed**: SBS MOFE build, global class-to-class landuse mutation,
  canopy override propagation, Forest acceptance, and production repair
- **Commit/branch context**: starting revision
  `714693a00c1ce47def86ba0b984065262b9f49bd`; implementation pending
- **Canonical contracts**: proposed
  `docs/schemas/mofe-management-artifact-contract.md` plus contracts named in the
  contract decision artifact; evidence claims follow
  `docs/standards/generated-artifact-validation-standard.md`
- **Related QA/security artifacts**: QA review pending; dedicated security review
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
| Single-OFE; MOFE never used | yes | Preserve existing single-OFE behavior | pending regression |
| MOFE state absent before build | conditionally | Build normally or return explicit build-first error for a mutation | pending regression |
| MOFE state present but empty | conditionally | No false treatment completion; follow operation contract | pending regression |
| Populated MOFE assignments | yes | Generate files from final assignments | pending real writer test |
| Supported legacy assignments | yes | Normalize without schema migration | pending regression |
| Malformed/incomplete assignments | no | Bounded explicit failure before completion | pending regression |
| SBS absent | yes | No burn remap | pending regression |
| SBS classified 130 | yes | Preserve unburned management | pending real SBS test |
| SBS classified 131/132/133 | yes | Select effective low/moderate/high management once | pending real SBS test |
| Explicit canopy override absent | yes | Preserve source/RAP behavior | pending regression |
| Explicit canopy override populated | yes | Apply stored value unless RAP currently supersedes it | pending 0.30/0.50 test |
| Writer working | yes | Remain pending; file existence is not success | pending boundary test |
| Writer failed | no completed result | Existing exception path; no completion trigger | pending boundary test |
| Writer completed | yes | NoDb, landuse files, and summaries agree; prepared inputs are checked after normal WEPP preparation | pending generated-output test |

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

- [ ] Canonical intent is named; implementation and tests are not treated as
      authority for user behavior.
- [ ] Absent, empty, populated, supported legacy, and hostile states are tested
      or explicitly ruled out.
- [ ] Input combinations and persisted/filesystem states are reviewed separately.
- [ ] Direct generated-content tests exercise each of the three changed producer
      paths.
- [ ] Mocks do not replace SBS classification or the writer boundary that caused
      the production failure.
- [ ] Existing authorization, locking, and containment preserve every valid state.
- [ ] Existing failure behavior is preserved without adding recovery machinery.
- [ ] Errors and recovery guidance are understandable and actionable.
- [ ] Existing workflows remain compatible except for corrected generated bytes.
- [ ] Coverage claims name all covered dimensions and direct evidence.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Full SBS MOFE build | Classified severity is translated again and defaults burned segments to unburned | Incident evidence and source path | Consume classified code once; add real SBS regression | Open |
| COR-02 | High | Global class mapping | Persisted assignments change without regenerating combined management files | Incident evidence and RQ source path | Regenerate before completion; test writer failure | Open |
| COR-03 | High | Canopy thinning | Stored 0.30/0.50 overrides are ignored during MOFE synthesis | Production files and segment-plan source | Propagate explicit override while preserving RAP | Open |
| COR-04 | High | Validation/release | Prior actual-project job was called fixed without generated-file readback | September 7 clone and prior validation artifact | Make actual Forest content evidence a hard gate | Open |

## Verdict

- **Implementation gate**: PASS, independent `correctness_review`, 2026-09-18 UTC.
- **Implementation findings**: COR-01, COR-02, COR-03 resolved by direct artifact
  tests and bounded source correction. No unresolved High/Medium code finding.
- **Release recommendation**: hold for COR-04, actual Forest acceptance.
- **Reviewer scope**: source and tests, including public canopy edit, retained
  MOFE overrides, real SBS classification, generated/prepared managements, writer
  failure/retry, absent state, and nonsequential segment IDs. Local tests isolate
  NoDb locking and unrelated slope/soil preparation; they do not prove deployed
  workflow equivalence.

## Artifact Observability Gate

- [ ] Comparable project layout and canonical artifact inventory are named in the
      canonical contract.
- [ ] Existing inputs and generated outputs remain visible through the normal
      project boundary.
- [ ] Real writer/failure tests and Forest evidence inspect generated content.
- [ ] No new hidden storage or artifact boundary is introduced.
