# Execute the dedicated query catalog queue

## Purpose

Implement the [work package](../../package.md) against the catalog routing contract. The authorized image includes the pinned native updates and landing-page changes already integrated at 160fb12b1.

## Progress

- [x] Pin the starting revision and document the authorized topology, scope and validation.
- [ ] Change enqueue, reconciliation, consumer readiness, Compose and deployment assumptions; validate compatibility, migration and rollback.
- [ ] Run scoped tests and the RQ graph check, obtain independent reviews and merge through a protected PR.
- [ ] Build one retained candidate on wepp1; validate native artifacts and security evidence, transfer by digest and apply host-specific bindings.
- [ ] Fence admission and fetches as appropriate. Recheck job functions before stopping authorized catalog refreshes. Preserve other running jobs and durable receipts. Activate hosts sequentially, verify identities, restore dispatch and confirm received work.
- [ ] Validate real artifact publication and coexistence on the production NFS clients; record residual risks and follow-up freshness observation.

## Surprises & Discoveries

The wepp3 Rocket client uses NFSv3 with soft timeouts. The wepp1 client uses NFSv4.2 with hard timeouts. Test cross-client record locks and read/replace semantics before worker activation.

## Decision Log

Keep fork/archive serial and dedicated. Preserve default backlog deferral initially. The catalog uses a distinct consumer on wepp3 to isolate occupied RQ slots. Queue routing alone cannot isolate NFS operations. Leave rq/info-details untouched. Use a bounded admission pause during mixed-version rollout; avoid flushing RQ or deleting pending receipts.

## Outcomes & Retrospective

Record exact merged revision, image, deployment disposition, job and readback evidence in the tracker. A missing or incompatible consumer must leave a recoverable receipt. Rollback uses the retained prior artifact, restores queue topology and rediscovers durable pending work.
