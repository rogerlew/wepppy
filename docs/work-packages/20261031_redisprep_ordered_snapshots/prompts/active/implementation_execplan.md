# Execute RPS-01 atomic ordered RedisPrep snapshots

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Work from `/home/workdir/wepppy` on existing `master`; do not deploy or submit
production jobs. The complete operator acceptance matrix is retained at
`../../artifacts/operator-prompt.md` and is part of this execution scope.

## Purpose / Big Picture

A successful metadata setter should leave a complete recoverable snapshot whose
publication cannot run backward. Cold recovery should expose coherent timestamps
and receipts without overwriting newer live updates. Prove this by parsing the
file, restoring through RedisPrep, and inspecting a real downstream consumer.

## Progress

- [x] (2026-10-31 14:32 UTC) Recorded revision/status, inspected primary and related writers, read applicable guidance and skills.
- [x] (2026-10-31 14:32 UTC) Drafted canonical contract, authority/compatibility checkpoint and bounded package.
- [x] (2026-10-31 UTC) Two independent reviews complete; presentation findings closed. Historic damaged-state acceptance remains an explicit operator decision.
- [x] (2026-10-31 UTC) Operator approved legacy reconciliation limit and checkpoint commits 88b5c174f / ea95e1298.
- [x] (2026-10-31 UTC) Implemented atomic writer, ordered capture, conditional recovery and direct consumers.
- [x] (2026-10-31 UTC) 52 real Redis/NFS snapshot tests, 183 consumer tests and 199 preservation tests pass.
- [x] (2026-10-31 UTC) Independent correctness/security/QA reviews and stub/exception gates pass.
- [x] (2026-10-31 UTC) Broad continuation: 8,619 passed / 295 skipped; docs, source manifest and diff checks pass.
- [ ] Before rollout: cross-host lock, alias, ACL and authenticated browse parity (outside this local delivery).

## Surprises & Discoveries

- `flock` does not coordinate the supported NFS/local-ZFS pairing; catalog uses
  POSIX record locks plus thread exclusion and stable external managed locks.
- Archive restore preserves directory inode; inode-only incarnation fencing fails.
- RedisPrep basename identity differs from NoDbBase nested/group identities.
- Fork reset deletes the shared hash before rebuilding fields; preflight reads
  HGETALL without gating on loaded, making partial restore directly observable.
- A historic partial restore that already exposed true readiness is inherently
  ambiguous against later legitimate deletion without new provenance.

## Decision Log

- 2026-10-31 / Codex: treat as new contract extension, not NoDbBase conformance;
  existing source-of-truth rules do not apply to this helper.
- 2026-10-31 / Codex: prefer existing filesystem lifecycle coordination, but
  require lock-order/access/namespace proof before implementation. Reject rename-
  only and expiring-lease-check fencing as insufficient.
- 2026-10-31 / Codex: preserve flat schema and namespace semantics; surface
  unresolved collisions/legacy ambiguity instead of inventing migration.

## Outcomes & Retrospective

Implementation and direct consumers are wired and locally verified. Checkpoint
ancestors are committed; operator authorized implementation commit and push. No deployment.
See artifacts/validation.md for final split-run results, performance cost and limits.
Local delivery is complete; package remains open for external rollout parity.
Local filesystem is ext4; `/wc1` is NFSv4.2 with `local_lock=none`. This mount
observation is not multi-host identity/locking validation.

## Context and Orientation

`wepppy/nodb/redis_prep.py` wraps Redis DB 0, separate from NoDbBase singletons.
Its `dump` truncates a flat JSON file; `lazy_load` writes fields individually.
`project_rq_fork.py` has a separate atomic copied-snapshot reset; `project_rq.py`
rebuilds its hash. Archive, Omni, postfire, WEPPcloudR and submission recovery
consume or mutate this metadata. See `../../artifacts/consumer-matrix.md` for
paths and unresolved variants. Current authority is
`docs/schemas/redisprep-snapshot-contract.md` with the checkpoint's preserved
cross-cutting contracts.

## Plan of Work

First finish consumer/field/namespace inventory and independent contract reviews.
After explicit commit authority, commit only the accepted checkpoint files and
record revision/ancestry. Do not include unrelated tracker hunks or research.

Before production edits, characterize failure with deterministic real-file
replays. Evaluate reuse of catalog lifecycle guards, their managed namespace and
incarnation identity, and acquisition from existing NoDb/submission callers.
A protocol must hold cross-process exclusion from capture to replacement, bind
wrappers to lifecycle identity, and atomically condition Redis recovery. Preserve
ordinary and standalone path compatibility. If reuse adds a deadlock or fails
real acceptance, retain the evidence and smallest alternative cost; do not
silently create another lock framework.

Implement in RedisPrep plus only confirmed direct reset/mutation/lifecycle
consumers. Multi-field Redis mutations must be coherent. Keep payload flat and
locked fields out of restoration. Publish with same-directory exclusive staging,
short-write handling and mode/access preservation. Distinguish postcommit failures.
Update affected developer/operator docs in the implementation change.

## Concrete Steps

1. Read checkpoint and matrix, finish independent review disposition.
2. Commit checkpoint only after authority; record `git rev-parse HEAD` in tracker.
3. Add targeted tests and minimal implementation sequentially, using `wctl run-pytest`.
4. Run fork, submission recovery, postfire and WAM/MRS/NFMS regression anchors.
5. Run `wctl run-pytest tests --maxfail=1`, `wctl check-test-stubs`, relevant stubtest,
   broad-exception changed-file gate and code-quality observability.
6. Run `wctl doc-lint --path` for changed docs and preview `uk2us` differences.
7. Obtain independent correctness/security/QA reviews; close medium/high findings.

## Validation and Acceptance

Implement the full operator-prompt regression matrix, retaining each result or
blocker. Two real processes and isolated real Redis must prove snapshot order;
threads/test doubles alone cannot. A/B capture, direct deletion, live writer vs
loaders, kill before replace, all filesystem failure stages and lifecycle restore
must yield the defined final JSON and normal-reader consumer semantics. Preserve
RQ jobs when simulating metadata loss. Test valid empty/fresh/legacy states and
access under representative identities, including NFS. Report p50/p95 startup
and setter latency with payload sizes and mount/identity context. Final review
must not confuse local passes with production-equivalent validation.

## Idempotence and Recovery

Use only unique disposable runs/keys. Never flush Redis or clear foreign locks.
Retain original corrupt snapshots and last good bytes on precommit failures.
No automatic rollback after replacement. Temporary files are ownership-scoped;
orphans are not authoritative. Missing directory writes do not recreate runs.
No branch/dependency/deployment changes. Commit only named package/contract files.

## Artifacts and Notes

Retain contract reviews, decision/disposition, consumer matrix, reproducible
scripts/test commands, parsed snapshot/consumer evidence, performance/access/mount
results and final reviews under `../../artifacts/`. Update tracker alongside this
plan at every milestone. Local implementation evidence supports the bounded repair, not production rollout.

## Interfaces and Dependencies

Preserve RedisPrep public getter/setter signatures, task enum and flat JSON.
Use installed Redis/filesystem/Python tools. No new dependency. Any new public
helper must have matching stubs and consumers; no silent fallback wrappers.

Revision note: initial plan records investigation and checkpoint gate before
implementation, including the legacy/mount/namespace constraints found in source.

## Operator approval — 2026-10-31 UTC

Operator answered "yes" to committing this reviewed checkpoint and proceeding,
including explicit reconciliation for already-partial legacy hashes with a true
loaded marker. Commit authority and that acceptance disposition are granted.
Implementation and local environment validation are complete; broader rollout parity remains open.

## Implementation decisions and final evidence — 2026-10-31 UTC

A short blocking serializer precedes nonblocking lifecycle acquisition. This
retains existing lifecycle exclusion while ordinary parallel setters wait safely;
actual kernel contention and two real batch leaf initializations exercise it.
No model execution runs under this guard. First catalog initialization is marked
explicitly so existing wrappers may adopt it once; destructive replacements never
qualify. Held directory descriptors prevent inode reuse from defeating fencing.

Archive restore durably rotates the root identity before destruction and preserves
its coordination files across failure/kill. A second rotation after extraction
retains existing copied-request/nested-identity retirement. Nested snapshots are
artifacts only; activating their basename hashes could overwrite unrelated runs.

Redis EXEC response loss and filesystem publication uncertainty are explicit
error states. Already committed Redis updates are never described as rolled back
when disk publication fails. Shared recording stubs test API shape only; disposable
real Redis/process tests establish concurrency. Wrapper descriptor churn has zero
net growth after 1,000 constructions. NFS setter median rises from 2.51 to 9.94ms
for a 1,887-byte payload; this is the measured durability/coordination cost.

Broad validation began before the final mock assertions changed: 3,958 passed,
125 skipped, one stale assertion failure. Continue from that module on current
files and retain exact file list/log; do not call this one final-revision full pass.

Revision note: records approved ancestors, wired implementation, independent
review closure, real artifact results and explicit production-parity limits.

Final validation: current-file continuation completed with 8,619 passed and
295 skipped in 1,893s. The earlier 3,958 passes are historical partial-run
evidence, not one exact-final-candidate full pass. All 52 snapshot cases passed
separately on NFS/real Redis. Cleanup removed only owned disposable server/scratch.
No deployment; remaining parity gate is explicit, not an inferred approval.

Delivery authorization: operator requested “commit and push” after reviewing the
implementation handoff. Commit the bounded repair and push the current master;
preserve unrelated workspace changes. Deployment remains outside scope.
