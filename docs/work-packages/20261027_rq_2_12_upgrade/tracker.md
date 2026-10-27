# RQ 2.12.0 upgrade tracker

**Status**: Active — compatibility inventory and baseline  
**Updated**: 2026-10-27 19:10 UTC

## Progress

- [x] Confirmed hostname forest, local Docker context, development wctl preset and running stack.
- [x] Recorded scope, complexity budget and operator authorization.
- [ ] Independent contract checkpoint reviews and standalone ancestor revision.
- [ ] Compatibility inventory and 1.16.2 baseline.
- [ ] Exact dependency resolution and minimal implementation.
- [ ] Real Redis/worker regression coverage and historical-state fixtures.
- [ ] Rebuilt forest API/model/artifact acceptance and isolated rollback proof.
- [ ] Required gates and independent correctness/security review closure.

## Decisions

2026-10-27 19:10 UTC: operator authorized exact 2.12.0 upgrade preserving application contracts, with native webhooks disabled/unexposed. No mixed-version safety or reverse-state compatibility is assumed. Required checkpoint commit is authorized by the explicit request for an ancestor revision; no push or branch change.

## Evidence and risks

Starting HEAD `9231f2427d33b64f971992ac969fd9420c49afd3`. Unrelated Roads Python/template/test/docs edits and two dev notes are preserved. Inventory and baseline agents are read-only. No runtime has changed. Historical queued/deferred/scheduled/running/completed/failed state support remains unverified and blocks cutover claims.

## Next action

Complete checkpoint reviews while inventory and existing tests run. Select bounded disposable model fixture before any runtime upgrade. Record exact acceptance commands and evidence as discovered.
