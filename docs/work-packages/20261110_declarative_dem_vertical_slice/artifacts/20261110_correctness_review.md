# Correctness and User-Experience Review — Declarative DEM vertical slice

## Metadata

- Reviewer: independent agent `/root/dem_contract_correctness` (`reviewer`).
- Reviewed: 2026-11-10, through 21:51 UTC.
- Contract ancestor: `d6e101ab8f047f6be64283280bc128ceab66163e`.
- Candidate: implementation working tree after that ancestor; final implementation
  commit and deployment are not implied by this review.
- Scope: `wepppy/declarative/`, `tools/declarative_dem.py`, shared RQ execution,
  NoDb mutation, HTTP admission, Bootstrap, archive and project presentation changes.
- Authority: [DEM v1 contract](../../../schemas/declarative-dem-v1-contract.md),
  particularly Protection and lifecycle, Finalization authority and command results,
  Visible records and publication, and Selected consumer and fixture.
- Related: [contract reviews](20261110_contract_reviews.md),
  [security review](20261110_security_review.md), [validation ledger](validation_matrix.md).

## User outcome and review boundary

The operator requests a public DEM project with attributable execution, protected
completion and subsequent map elevation viewing. Verified success requires actual
task/image binding, a valid raster, required Git checkpoints and read-only
finalization. Failure retains the project and distinguishes processing failure,
uncertain execution and incomplete protection. Existing ordinary projects retain
their behavior when declarative metadata is absent.

This is an implementation review, not cluster acceptance or deployment approval.
The selected consumer is explicitly the existing zero-write HTTP elevation query.
It is not an RQ report task. Public-only admission avoids claiming private-source
authorization in that existing unauthenticated service.

## Valid-state and input coverage

| State | Required outcome | Direct evidence inspected |
| --- | --- | --- |
| Absent admission / legacy ordinary project | Preserve ordinary mutation and DEM behavior | `test_ordinary_empty_and_invalid_states`; existing ordinary suites remain required |
| Present-empty provenance directory | Ordinary behavior; no false protection | Same direct filesystem test |
| Empty, malformed or symlinked marker | Explicit mutation refusal | Same test and `test_symlinked_record_rejected` |
| Valid admission | One science attempt; duplicate submission observes it | `test_adapter_full_lifecycle_with_fixture_runtime_identity` |
| Completed protected build | Read-only viewer succeeds without changing protected bytes | Same lifecycle test; `test_real_raster_and_zero_write_consumer` |
| Superseded project incarnation | Refuse stale diagnostic publication; preserve ordinary science | `test_observation_refuses_replaced_project` |
| Interrupted archive restore | Preserve admission and READONLY fence | `test_interrupted_declarative_restore_retains_fence` |
| Failed source, checkpoint, initialization or finalization | Retain truthful failure; no replay or verified success | Parameterized integration lifecycle fault cases |
| Invalid DEM grid | Retain failed attempt and raster; finalize failure read-only | Independently executed `invalid_grid` lifecycle case |
| Canceled queued science | Remain canceled after protection; no scientific execution | Integration `cancel` case and CLI result test |
| Revoked image approval | Deny new admission; retain status/cancel control | `test_revoked_approval_does_not_block_existing_control` |
| Invalid image/source/visibility/extent/identity/JSON | Reject before admission | Definition and runtime-evidence tests in `tests/rq/test_declarative_dem.py` |

The matrix does not assert exhaustive coverage. Actual running-worker cancellation,
Pod loss, Kubernetes identity, real provider behavior and browser authorization
remain target-environment gates. Test input combinations and stored/filesystem
states are separate dimensions.

## Findings and disposition

| ID | Severity | Finding | Disposition and evidence |
| --- | --- | --- | --- |
| COR-01 | High | Destructive restore removed the only declarative fence before extraction. | Resolved in contract and implementation: preserve `provenance/` and `READONLY`; direct interrupted-restore regression inspects retained fence. |
| COR-02 | Medium | Finalization authority and reconnection protocol were undefined. | Resolved in the contract checkpoint: separate bound operational finalizer, observational status and guarded completion. |
| COR-03 | High | Restore accepted extra protected files, including `dem/dem.vrt`, which changes viewer selection. | Resolved in `archive.validate_restore`: exact protected inventory; direct archive tests cover extra VRT, NoDb and aliased paths. |
| COR-04 | High | Completion could bless raster bytes different from the science checkpoint. | Resolved in `_verify_science_boundary`: checkpoint/digest/consumer-path checks and detached Ron readback; direct drift/alternate-viewer regression. |
| COR-05 | Medium | Invalid owner/initialization failure left a public admitted project with no failure disposition. | Resolved: prevalidate owner; retain `science_not_dispatched` failure and bounded finalization path. Integration `initialize` fault tests retained failed protection. |
| COR-06 | Medium | Duplicate completion rewrote historical build bytes. | Resolved by observational return for verified state; full lifecycle test asserts unchanged `build.json` bytes. |
| COR-07 | Medium | Observation publication checked marker equality without incarnation identity. | Resolved with directory/incarnation capture and locked revalidation; direct replacement regression. |
| COR-08 | Medium | ZIP marker aliases bypassed rejection when restoring into an ordinary project. | Resolved by normalized member detection; direct ordinary-target preservation regression. |
| COR-09 | Medium | Finalizer preflight/claim/protected-manifest failures preceded its failure handler, leaving protection pending and no durable error. | Resolved: first-attempt preflight/publication is inside the failure boundary; duplicate claim refusal remains outside. Integration drift/manifest/finalization faults assert durable failed protection. |
| COR-10 | Medium | CLI required current image approval for status/cancel, preventing control after approval revocation. | Resolved: shape validation is separate from new admission approval; command-level regression uses absent approvals. |
| COR-11 | Medium | Invalid-raster/grid readback raised before persisting the scientific attempt, losing effective-input/runtime failure evidence. | Resolved: retain sanitized failed attempt/checkpoint and original raster, then propagate failure. Reviewer independently passed the invalid-grid lifecycle case. |
| COR-12 | Medium | Successful protected cancellation always exited 1 because verified must remain false. | Resolved: settled canceled/readonly result without error is command success; verified remains false. Command-level regression covers exit status. |

Post-fix source confirmation completed for all findings. Changes made after this
review require review of their delta; this artifact is not blanket approval for
subsequent implementation changes.

## User-reachable error policy

| Condition | Classification | Required visible behavior |
| --- | --- | --- |
| Unsupported or malformed request | Expected admission refusal | Sanitized structured error; no scientific dispatch |
| Protected mutation or Bootstrap request | Expected refusal | Existing error envelope, `declarative_protected`, HTTP 409 after authorization |
| Source/scientific/semantic output failure | Exceptional build failure | Retained outputs and failed attempt; no verified success |
| Missing checkpoint or uncertain execution | Exceptional incomplete build | No automatic science replay; retain history and explicit recovery state |
| Finalization failure | Exceptional protection failure | Processing outcome retained; protection failed; ordinary mutation still prohibited |
| Later viewer failure | Independent request failure | Existing visible viewer error; historical build outcome unchanged |

## Generated artifact evidence chain

| Boundary | Evidence inspected | Limit |
| --- | --- | --- |
| Definition and effective map | Strict schema; real Ron initialization/map persistence in lifecycle test | Owner registration and Pod evidence are fixtures in that test |
| DEM writer and semantic parser | Real rasterio files; CRS/grid/content validation; actual elevation sampler | Lifecycle test substitutes `Ron.fetch_dem`; real provider acquisition is still required |
| Scientific checkpoint | Actual Git commits and record readback | Cluster mount/identity/umask validation remains pending |
| Read-only finalization | Real RQ and NoDb integration flow; manifest/READONLY assertions | Target deployment workflow still required |
| Queued refusal | Real worker rejection and FailedJobRegistry integration test | Does not alone cover every direct/API entry point |
| Archive/restore | Canonical writer/extractor tests, member rejection, preserved bytes and interrupted cleanup | Live browse/download and cluster archive acceptance remain pending |
| Later viewing | Actual DEM sampling and unchanged protected hashes | Live browser POST under target deployment remains pending |

Reviewer-executed command:

```sh
wctl run-pytest tests/rq/test_declarative_dem_integration.py -k invalid_grid -q
```

Result: **1 passed, 9 deselected, 4 warnings in 14.36 s**. Warnings concern existing
dependency deprecations and Python's multithreaded-fork warning. The real RQ worker
completed this failure/protection case; the raster source and runtime identity
remain explicit fixtures. The primary agent reported the preceding 31 focused
checks passed and owns broader command results in the validation ledger.

No runtime acceptance is inferred from broad pass counts or file existence.
The reviewer did not run a live acquisition, deploy a worker, or exercise the target
browser. Existing-user SQL registration is reused but mocked in the new lifecycle
fixture; actual account ownership belongs in target acceptance.

## Verdict

**Local implementation correctness: pass for the reviewed candidate.**
Unresolved high/medium code findings: **0**. This supports preparing the operator
handoff after the remaining repository gates pass; it does not authorize live
deployment or close the work package.

The package remains open through real provider acquisition, Kubernetes runtime
identity verification, browser/download acceptance, running cancellation/worker
interruption evidence and overhead measurement. Production-equivalent identity,
mount and umask checks must precede rollout under the target repository's rules.

## Artifact observability

Visible records use the normal `provenance/` project tree. Canonical archive
tests prove member coverage and byte equality, including preservation through
interrupted restore. The existing build-record path precedes read-only manifest
creation. Live normal browse/download and restored-project viewing remain explicit
acceptance gates; no hidden-only artifact exception is claimed.
