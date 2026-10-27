# Shared-batch pilot execution security review

Reviewer: `pilot_security`, October 27, 2026. Scope: executing the existing
bounded pilot after the operator-authorized full deployment of `0da9c9071`.
Security impact: **high** because trusted control crosses shared queue and
production filesystem boundaries. This is an execution-evidence gate, not a
repeat implementation review or authority for general asynchronous enablement.

## Findings and verdict

**PASS for the completed bounded shared-batch pilot.** No unresolved high,
medium or low security finding. This verdict covers the retained execution and
its stated limits; it does not approve general enablement or whole-fleet capacity.
No production mutations or runtime code edits were performed by this reviewer.

The retained [deployed preflight](20261027_shared_pilot/deployed_preflight.json)
passes the source/configuration check: wepp1 and wepp2 match all six retained
source hashes, native-library hashes and selected dependency versions, run as
1002:130, report eight compatible unsuspended consumers and zero queued batch
jobs, and retain general async disabled. This is admission evidence, not proof
of successful execution or whole-fleet capacity.

All five application/controller SHA-256 values match the final independently
reviewed values in [the implementation security review](20261027_pilot_implementation_security_review.md).
The cancellation-after-claim finding remains closed in those unchanged sources.
The earlier source-only/backport rollout description is historical; the current
execution must retain actual full-deployment image/source identities instead.

## Security boundaries checked

- **Authority and valid states:** no new public endpoint or token authority.
  General disabled-mode producers and scheduler remain synchronous/disabled as
  contracted. Only an existing immutable operator manifest can authorize the
  eight fresh owned scratch scopes; the excluded sentinel remains outside it.
- **Filesystem and data integrity:** exclusive fixture creation, canonical paths,
  owner markers, scope/namespace/incarnation/inode bindings and worker-side
  revalidation prevent implicit expansion to neighboring projects. Retained raw
  catalog and receipt verification precedes potentially repairing consumers.
- **Queue and recovery:** queue-wide seven-outstanding cap, retry-inclusive
  25-refresh/two-inventory budgets, original 1,800-second admission window,
  single-use execution claims, conservative cancellation accounting and latched
  pause remain in force. Existing ordinary work is never preempted for the pilot.
- **Observation:** the controller renews its 60-second lease only after observed
  state; 10-second samples cover admission and drain. Missing observation or
  uncertain accounting cannot become a success claim. Raw ordinary-job metadata
  is read without task deserialization or registry cleanup.
- **Secrets and disclosure:** no changed credential flow, public routing or
  external egress. Evidence must stay operator-owned/private; only sanitized job
  trees and necessary execution summaries may enter retained review artifacts.
- **Deployment and supply chain:** the user separately authorized the full
  canonical rollout. Actual image/source/configuration readback and eight genuine
  compatible worker registrations remain required; old local image-derivation
  tests cannot stand in for current production parity.

## Independently checked execution evidence

Inspected the private local review copy of the operator evidence:
deployed/registration preflight, setup and
registration, pause result, lease-rejection log, final result, observations,
worker registrations and both artifact readbacks. Raw pilot identifiers, fixture
paths and ordinary-job identities are intentionally not reproduced here.

- Final outcome is `completed`, with admission paused for
  `acceptance_readback_complete`. All **17 jobs finished**: one inventory and
  sixteen refresh jobs. Ledger counters equal the binding-kind counts; final
  pilot/global outstanding and global uncertainty are zero, with no failures.
- The original manifest, configuration, generation, deadline and budgets are
  identical in pause and final snapshots. Early resume was rejected while the
  prior observation lease remained owned; the successful explicit resume did not
  reset consumed inventory budget or the original admission window.
- All job `worker_name` values match the suffixes of retained `rq:worker:`
  registration keys. Eight registrations carry the same approved configuration;
  actual jobs ran on both expected batch-container hosts. The Redis hash's absent
  optional `name` field is not a missing registration.
- Both artifact readbacks pass for eight scopes and 24 query comparisons each:
  **48 source-versus-copy consumer comparisons** in total. The reviewed controller
  checks all 79 source Parquet hashes/schemas, scope identity, raw publication
  digest and receipt acknowledgment before the consumer checks, and confirms
  consumers did not change those publications. Both snapshots report unchanged
  source and excluded sentinel.
- Negative-control completion is retained. Every public job tree has the generic
  maintenance description, no children, and no run ID, result, exception or
  authentication actor payload.
- Twelve retained samples report eight compatible unsuspended consumers, no
  incompatible participants, no uncertainty/failure and at most **four sampled**
  outstanding maintenance jobs. This sampled maximum does not replace the
  atomic seven-job admission bound or prove the continuous maximum.

### Observation and capacity limits

There is an explicit **90.32-second observation gap** during the intentional
paused/drained controller restart. The only admitted inventory job had finished
before that gap; no refresh was admitted until after the new observer's first
sample. Retained pause/final accounting proves no admitted pilot execution spans
the gap. This demonstrates safe explicit restart; it is not uninterrupted
ordinary-queue monitoring.

One ordinary batch job was already running when observation began. Its recorded
enqueue-to-start wait was **8.013 ms**. No waiting ordinary backlog was observed;
delay under newly competing ordinary arrivals was not exercised. Neither that
sample nor the eight copied fixtures establishes whole-fleet throughput or
ordinary-job delay guarantees.

## Owned-resource disposition

The final paused ledger and zero outstanding work satisfy activity cleanup.
Parent-proposed retention outside managed roots is acceptable only as separate
post-acceptance maintenance: recheck each exact one of the nine marked fixture
identities inside its lifecycle guard, invalidate its incarnation, then rename
to an absent destination in the private retained-fixtures directory. Preserve
pre-cleanup sentinel/source snapshots, external guard files, all receipts and the
original Redis ledger/budgets. Do not touch source or user projects, delete queue
accounting, reuse pilot budgets, or claim post-invalidation sentinel bytes stayed
unchanged. The final readback below dispositions the completed cleanup.

### Final cleanup readback

The retained cleanup and cleanup-readback JSON now confirm all nine original
fixture paths are absent, the nine distinct retained destinations are outside
managed roots, the Redis ledger and external guards remain, and no observer lease
or outstanding pilot work remains. Eight compatible unsuspended workers remain
available and general async remains disabled. The parent verified all **711
retained Parquet hashes** and **eight catalog hashes**. This reviewer independently
checked that the cleanup source set equals exactly the eight frozen scope paths
plus sentinel, that old incarnations match the admitted bindings, that every new
incarnation differs, and that the published private-evidence digests match the
retained files. Cleanup disposition: **PASS** within the owned scope.

Evidence-retention limitation: canonical invalidation overwrote the original
refresh status/incarnation files before retention, without a separate copy of
their original bytes. The frozen manifest and already-checked controller
readbacks retain the original binding, publication digest and eight receipt
acknowledgment checks; scientific sources, catalogs and receipt history remain.
Exact replay of the original status JSON is therefore unavailable. This does
not reopen an authority, containment or successful-execution finding, but the
limitation must remain explicit and must not be described as complete raw-state
retention. Future cleanup should snapshot those small metadata files before
invalidation. See the [sanitized execution summary](20261027_shared_pilot/summary.json).

## Residual scope

Redis/Docker operator authority is trusted. The bounded pilot cannot establish
whole-fleet capacity or authorize general async enablement, even if every pilot
artifact passes. The preexisting legacy mount limitation remains outside scope
under the recorded operator decision. No new risk acceptance is requested.

Validation: source hashes independently recomputed; private JSON accounting,
worker lineage, public-tree sanitization and observation intervals independently
checked; `wctl doc-lint` passes for this artifact. No runtime code changed and no
prior exhaustive test suite was needlessly repeated.
