# Staley enqueue handoff conformance fix

Job `a6fed507-0d02-4eeb-9d47-8dd4268e559f` failed before raster processing:
its worker could not acquire the PostfireDebrisFlow NoDb lock held by rq-engine.
The enqueue route redundantly writes the job association after queue admission,
allowing the worker and producer to contend immediately.

Unchanged authority: `docs/schemas/nodb-persistence-concurrency-contract.md`
(writer ownership) and the module's `docs/production_m1.md` (exact allocated job
receipt before queue writes). Restore a single producer-to-worker handoff:
finish the queued receipt before admission and remove the successful post-enqueue
NoDb mutation. No schema, numerical engine, auth or artifact-retention change.

Compatibility/regression plan: retain exact job IDs and existing failure/recovery
contracts. Test an immediately starting worker that holds the real NoDb lock
when enqueue returns; producer must return its response without touching state.
Run focused route/production tests, required correctness review and actual worker
retry of the retained failed upload. Preserve failed source/status/error records.
The full suite was initially held, then authorized by the operator before commit.
No new retry loop or lock override.

## Completed validation

- Original regression reproduced NoDbAlreadyLockedError; 85 focused tests passed
  after the fix. Independent correctness review accepted.
- Forest development rq-engine was reloaded via wctl. No worker restart, lock
  deletion, broad retry wrapper, numerical change, or production fleet rollout.
- Actual browser retry completed as job `b83256cb-d503-40e5-9450-195ad0b3ed28`
  (2026-09-11 04:19:55-04:20:12 UTC). Worker and normal browser state/reload confirm
  current dNBR, Auto scale 0.001, complete watershed coverage and M1 ready to run.
- Successful attempt `0ab0d2a41ecb4b4aa76378aeb71b6834` retains the original failed
  source `72b501a860cd4520817e32e6ff46f1ef`; original failure diagnostics remain.
  Prior M1 results are stale after accepting a replacement upload, as contracted.
- RQ job-tree inspection, graph consistency, scoped docs lint and diff checks passed.
  Final full-suite validation passed; see [full validation](artifacts/full_validation.md).

See [correctness review](artifacts/correctness_review.md), browser/worker logs and
before/after regression logs in `artifacts/`. Durable handoff guidance is in
`wepppy/nodb/mods/postfire_debris_flow/docs/production_m1.md`, immediately after the
exact allocated job-ID receipt requirement.
