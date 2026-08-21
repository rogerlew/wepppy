# Correctness and User-Experience Review - Climate Multiple-Build Finalize Lock

## Metadata

- **Package**: `docs/work-packages/20260820_climate_finalize_lock/`
- **Reviewer**: Pending independent reviewer
- **Date**: Pending
- **Scope reviewed**: GridMET and Daymet multiple-interpolated build/finalize paths
- **Commit/branch context**: Pre-implementation scaffold
- **Canonical contract**: `docs/schemas/nodb-persistence-concurrency-contract.md`
- **Related QA/security artifacts**: `artifacts/2026-08-21_security_review.md`

## User Outcome

- **User goal**: Complete a multiple-interpolated climate build without losing
  work or overwriting newer climate settings.
- **Success presented to the user as**: RQ completion with current derived
  Climate state persisted.
- **Failures that may reach the user**: Explicit superseded/conflict result when
  relevant climate inputs changed; underlying collection failures.
- **Partial-state behavior**: Preserve existing artifact behavior; never report
  successful final persistence when the finalizer did not commit.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Climate file absent | no for build | explicit existing initialization failure | Pending |
| Climate present, derived outputs empty | yes | collect and finalize | Pending |
| Climate populated | yes | replace only derived output fields | Pending |
| Supported legacy payload | yes | preserve unrelated fields | Pending |
| Malformed payload | no | bounded explicit decode/validation failure | Pending |
| Unrelated concurrent rewrite | yes | preserve rewrite and finalize | Pending |
| Relevant concurrent rewrite | yes | supersede without mutation | Pending |

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Concurrent finalization | Implementation and direct boundary evidence do not exist yet | Scaffold | Complete implementation and unmocked interleaving tests | Open |

## Verdict

- **Gate status**: fail
- **Unresolved findings**: High 1; Medium 0; Low 0
- **Release recommendation**: hold
- **Reviewer sign-off**: Pending
