# Correct batch Climate and RAP NoDb contention

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current, and synchronize
`../tracker.md` at every stopping point. Follow
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, large batch watersheds can build observed GridMET/PRISM
climates and RAP time series without a controller invalidating its own NoDb
mutation base during threaded work. The stale-write guard remains strict:
unrelated concurrent changes survive, relevant input changes explicitly
supersede collected results, and no stale object is blindly dumped again.

Demonstrate the outcome with direct real-file interleaving regressions and an
operator-authorized forest replay of the affected batch. The replay must show
no new target `NoDbStaleWriteError` for `climate.nodb` or `rap_ts.nodb`, and
batch metadata must correctly distinguish completed and failed watersheds.

## Progress

- [x] (2026-09-07 05:34 UTC) Captured the production recurrence and exact job
  examples.
- [x] (2026-09-07 05:34 UTC) Linked canonical contracts and prior hardening.
- [x] (2026-09-07 05:34 UTC) Scaffolded the executable package.
- [ ] Attribute all writes in the two failing paths.
- [ ] Add failing direct regressions.
- [ ] Complete any required standalone contract checkpoint.
- [ ] Implement and validate Climate correction.
- [ ] Implement and validate RAP_TS correction.
- [ ] Validate batch failure/result consistency.
- [ ] Complete independent reviews and forest acceptance.

## Surprises & Discoveries

- The outer `clear_nodb_file_cache(..., "climate.nodb")` and fresh
  `Climate.getInstance()` are deployed and execute before `Climate.build()`;
  recurrence proves initial hydration was not the complete contention model.
- The failing observed GridMET path logs PRISM revision and many hillslope
  thread-pool submissions. The prior multiple-interpolated Climate package does
  not prove this path uses its finalized-result service.
- RAP_TS performs year/band analysis in a thread pool while its controller is
  inside a long `locked()` region, then publishes parquet/controller state and
  a RedisPrep timestamp. The exact writer invalidating its signature still
  requires a deterministic trace; do not assume threads mutate the controller
  merely because they compute into a shared in-memory dictionary.
- RQ reports `Job OK` because the batch wrapper returns a false result instead
  of re-raising. StatusMessenger still emits `EXCEPTION_JSON`; these are two
  distinct status layers.

## Decision Log

- Decision: preserve strict stale-write enforcement and use explicit
  controller-owned finalization.
  Rationale: the canonical NoDb contract forbids retrying a stale dump and
  treats the entire controller as one persistence scope.
  Date/Author: 2026-09-07, Codex from operator incident evidence.
- Decision: investigate copied `202606` logger identity but do not declare it
  causal without cache/lock/path evidence.
  Rationale: the rejected target is the correct `202608` path, so logger text
  alone does not prove cross-run persistence.
  Date/Author: 2026-09-07, Codex.
- Decision: contract-gate any change to RQ completion/trigger semantics.
  Rationale: persistence correction is established; whether a false tuple is a
  successful RQ job is a separate externally observable contract question.
  Date/Author: 2026-09-07, Codex.

## Outcomes & Retrospective

Scaffold only. Implementation, reviews, and forest acceptance remain pending.

## Context and Orientation

`NoDbBase` serializes each controller as one whole `.nodb` file. A hydrated
instance remembers the file `(mtime, size)` signature. `dump()` rejects its
write if the durable signature changed, preventing lost updates. A distributed
lock coordinates participating writers, but a long operation can still retain
a mutation base across internal or external writes.

The batch entry point is `wepppy/rq/batch_rq.py::run_batch_watershed_rq`. It
loads `BatchRunner`, whose `run_batch_project()` in
`wepppy/nodb/batch_runner.py` invokes Climate and RAP_TS stages. Climate mode
routing spans `wepppy/nodb/core/climate.py`,
`climate_build_router.py`, `climate_mode_build_services.py`, and
`climate_build_helpers.py`. RAP logic is in
`wepppy/nodb/mods/rap/rap_ts.py`.

The canonical behavior is in
`docs/schemas/nodb-persistence-concurrency-contract.md`. The scoped-cache guard
standard explicitly says cache invalidation does not make independent
whole-object read-modify-write operations safe.

## Milestone 1: Reproduce and attribute

Build deterministic tests around real temporary `.nodb` files. Reproduce an
equal-size intervening rewrite so the old code raises the same stale exception.
Do this separately for the observed Climate route and RAP_TS analysis. Do not
mock `NoDbBase.dump()`, `os.stat`, the lock, or durable hydration at the safety
boundary.

Instrument tests or temporary diagnostics to record controller class, wd,
runid, lock key/token, cache key, pre/post signature, call site, and thread/
process identity for every relevant dump. Remove noisy temporary diagnostics or
promote a bounded, secret-free attribution log before final review.

Trace these specific candidates:

- intermediate `Climate.dump()` calls such as seed initialization;
- PRISM revision and hillslope helper persistence/catalog callbacks;
- mode-router/facade final dumps;
- RAP raster acquisition, analysis, parquet publication, controller assignment,
  and RedisPrep timestamping;
- copied-run hydration and any retained base-run identity.

Acceptance: tests fail before implementation for the production signature and
the tracker names the exact invalidating writer(s), rather than inferring solely
from timing.

## Milestone 2: Establish contract authority

Classify the fix as conformance to the existing collect/finalize clause or a
behavior change. If existing authority is sufficient, record that with exact
section references. If new conflict, publication-order, or RQ semantics are
required, amend the canonical contract in a standalone ancestor commit and
complete the accepted contract-decision checkpoint before production edits.

Do not rewrite a closed work package as authority. Promote any reusable rule to
the canonical NoDb contract or a current standard.

## Milestone 3: Correct Climate ownership

Refactor only the reproduced observed GridMET/PRISM path. Keep expensive remote,
CLIGEN, raster, and hillslope collection outside the controller mutation lock.
Capture an explicit relevant-input snapshot and return only explicit derived
outputs. Under a short finalization lock, freshly hydrate the durable Climate,
compare relevant inputs, apply an allowlist of derived fields, and commit once.

Reuse the semantics and types from the prior multiple-build finalizer where
they fit. Do not force unrelated climate modes through a speculative abstraction.
Do not retry the original stale object or merge arbitrary attributes.

Acceptance: unrelated same-size rewrites are preserved, relevant changes yield
an explicit superseded/conflict result, collection failure does not mutate
controller state, and existing generated files remain compatible.

## Milestone 4: Correct RAP_TS ownership

Separate RAP acquisition/analysis collection from controller finalization where
the reproduction shows a long-lived mutation base. Define the relevant input
snapshot: at minimum year range, map/spatial identity, multi-OFE mode, band set,
and any inputs proven to affect the derived result. Define an explicit output
allowlist and publication order for parquet plus controller state.

Finalize against a fresh RAP_TS instance under its lock. A relevant change must
not publish stale results. A failure between artifact creation and controller
commit must leave a diagnosable, retryable state; use atomic temporary artifact
publication if the existing boundary requires it, without introducing a new
manifest subsystem.

Acceptance: direct regressions cover unrelated/relevant rewrites, missing and
empty source data, populated results, supported legacy controller state,
malformed state, and partial parquet/controller failure.

## Milestone 5: Batch outcome consistency

Verify rather than assume the intended contract for `run_batch_watershed_rq`.
At minimum, ensure failure metadata, `classify_batch_run_states()`, retry
selection, final summary, and StatusMessenger messages agree. Preserve trigger
compatibility unless a ratified contract authorizes change.

If changing false-result versus raised-exception behavior, first update the
applicable canonical RQ/batch contract in a standalone ancestor commit. Add job
tree/dashboard tests showing the intended RQ status and dependency behavior.
Update `wepppy/rq/job-dependencies-catalog.md` and run `wctl check-rq-graph`
only if enqueue sites or dependency edges actually change.

## Validation

Use the standard Linux forest development environment from repository root.
Discover exact existing module names before running commands; record any
adjustments in this plan.

Run focused tests covering:

    wctl run-pytest tests/rq/test_climate_rehydration.py tests/rq/test_batch_rq_retry_selection.py --maxfail=1
    wctl run-pytest tests/nodb/test_base_boundary_characterization.py tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py --maxfail=1

Add and run targeted Climate and RAP_TS modules for the real contention cases.
If public surfaces/stubs change, run the relevant `wctl run-stubtest` targets.
Before handoff run:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260906_batch_climate_rap_contention
    git diff --check

Complete independent correctness, code, QA, and security reviews with no
unresolved medium/high findings. Then, only under the operator's forest
authority, rebuild/deploy through the canonical workflow and replay a bounded
affected batch subset before a larger retry. Capture image revision/digest,
job IDs, queue state, exact error counts, artifacts, and rollback evidence.

## Idempotence and Recovery

Tests must use isolated temporary run trees and restore monkeypatches and
process state. Never clear production Redis registries or locks as a test
shortcut. Forest retries must use existing batch retry selection and preserve
failed-job evidence. A failed code rollout is recovered by the canonical image
rollback; a failed watershed remains explicit and retryable rather than being
marked complete.

## Artifacts and Notes

Record concise sanitized evidence in this package. Do not commit credentials,
full environment dumps, proprietary run inputs, or unbounded worker logs. The
job IDs, controller paths, timestamps, and exception signatures above are safe
diagnostic identifiers.
