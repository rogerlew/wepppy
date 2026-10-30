# WAM-01 correctness and QA review

## Metadata and authority

2026-10-30 UTC. Starting implementation revision
`29716c1bd9a24dacf1cb45e05a11b2aa44a5378e`; reviewed checkpoint ancestor
`525e78c9f` exists before implementation. User explicitly authorized that commit.
Canonical rule: `docs/schemas/wepp-run-input-contract.md`, WAM-01, with response
and webhook cross-links. Reviewers are independent of author `/root`.

## Correctness review

Reviewer `/root/implementation_correctness`: **production patch passes**; no
unresolved high or medium production findings. Verified the five endpoints
establish admission before applying inputs under the continuous existing lease.
Batch/base saves, early replay, bootstrap error mappings and prepared-file behavior
remain intact. No deployment or universal immutability/late rollback claim.

## QA review

Reviewer `/root/implementation_qa`, 2026-10-30 22:15 UTC: **pass for code quality**;
no unresolved high or medium findings, pending completed validation. Production
change remains bounded and readable; real persisted bytes, contention, replay,
saves and soil parameter readback are meaningful evidence. No refactor requested.

## Findings and disposition

| ID | Finding | Disposition |
| --- | --- | --- |
| QA-01 | Webhook tests left actual default-queue roots behind in shared disposable Redis | Resolved: track each owned root, delete with queue removal, compare queue deltas |
| QA-02 | Synthetic batch property lacked group_name required by real NoDb runid | Resolved: construct Wepp with actual batch/group_name identity |
| QA-03 | Missing-hint fixture attempted to delete an already-deleted RQ job during teardown | Resolved: remove deliberately deleted job from owned cleanup list |
| QA-04 | Normal lease reacquisition did not prove successor ownership preservation | Resolved: replace real Redis token during apply; successor remains and timestamp/receipt/enqueue stays untouched after lease loss |
| COR-02 | Real prep_soil evidence is not full worker-dispatch evidence | Accepted limitation: record exact writer boundary and no model execution claim |
| COR-03 | Original soil evidence used uploaded-input preservation for a normal project | Resolved: normal generated forest soil, persisted single-OFE state and reloaded options; 38 final tests pass and independent reviewer approves retained bytes/hash |

Both reviewers inspected the corrections; QA final response confirmed all four
fixture/coverage findings resolved. Final focused run after corrections:
237 passed, no skips; archive/browse compatibility: 72 passed. Full pytest passed: 12,210 passed, 334 skipped; final test-only fixture refinement
passed all 38 boundary cases separately.

## User outcome and state/error policy

Rejected proposed inputs stay unapplied on active root, active descendant, busy
lease or mismatched prior association. Valid fresh/terminal/missing hints and safe
deferred recovery remain retryable. Valid batch/base saves remain synchronous.
Shared-handler payload validation retains 400/capability-authority 409;
bootstrap retains 400. Input-lock 409 and exceptional persistence/enqueue 5xx
remain. Late application failure or lease loss does not promise rollback.
Full state/payload matrices and evidence paths: `assessment.md` and `validation.md`.

## Generated artifact evidence and observability

Request A (`kslast=0.03`) is persisted through real NoDb. B (`0.9`) is rejected
under contention and later with an active child after parent completion. Real
`prep_soil` consumes reloaded accepted fields and writes `wepp/runs/p1.sol`; parsed
restrictive conductivity remains 0.03. Path/hash/semantic receipt is retained in
`prepared-input-evidence.json`. No full dispatcher, full model output or report
freshness claim. Actual prepared-soil writer and durable files are not mocked;
HTTP auth/raster prerequisites and RedisPrep bookkeeping are isolated test doubles.

No artifact layouts, retention policies, browser auth, archive exclusions or
status conventions changed. Existing canonical archive/restore tests (including
working/failed/completed scientific records) and browse/raw/download tests pass.
These are local compatibility tests, not a live production browser observation.
Deployment and affected-resource repair are outside the authorized scope.

## Verdict

Correctness and QA approve the bounded implementation; no unresolved high/medium
findings. Local focused evidence passes. Final repository gate passed as recorded in `validation.md`; no deployment
authorization is implied.

## Final fixture consistency review

The author found and corrected an evidence-only mismatch: the original fixture
forced uploaded-input preservation for a normal project. Final fixture persists
single-OFE state, uses an existing generated forest `9002` soil fixture, and supplies reloaded normal clipping/
saturation options with `preserve_input_format=False`. Reviewer
`/root/implementation_correctness` independently confirmed these arguments match
the normal WeppPrepService writer path. Production code is unchanged; all 38
boundary tests passed on rerun (17.31s) and retained soil/hash evidence was refreshed. This remains
writer-boundary evidence, not full worker dispatch.

Final reviewer confirmation: retained soil SHA-256
`75431adbedee9bb4bfa611f684e3080959fb2144586b18511047b1535643f7a4`
contains restrictive conductivity 0.03 and initial saturation 0.4; normal-writer
evidence approved. No unresolved findings remain.
